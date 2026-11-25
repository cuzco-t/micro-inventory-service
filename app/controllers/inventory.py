"""
Inventory controller: Business logic for warehouse stock and fulfillment operations.
"""

from datetime import datetime
from typing import List, Optional
from sqlmodel import Session, select

from ..models.inventory import (
    LowStockAlert,
    StockReserveRequest,
    StockRestockRequest,
    WarehouseInventory,
    WarehouseInventoryCreate,
    WarehouseInventoryUpdate,
)


def get_all_inventory_controller(
    session: Session,
    offset: int = 0,
    limit: int = 100,
    warehouse: Optional[str] = None,
) -> List[WarehouseInventory]:
    """Retrieves all warehouse inventory records, optionally filtered by warehouse."""
    query = select(WarehouseInventory)
    if warehouse:
        query = query.where(WarehouseInventory.warehouse.ilike(f"%{warehouse}%"))
    return session.exec(query.offset(offset).limit(limit)).all()


def get_inventory_by_sku_controller(
    sku: str,
    session: Session,
) -> List[WarehouseInventory]:
    """Retrieves inventory positions for a specific SKU across all warehouses."""
    statement = select(WarehouseInventory).where(WarehouseInventory.sku == sku)
    return session.exec(statement).all()


def get_inventory_by_product_id_controller(
    product_id: int,
    session: Session,
) -> List[WarehouseInventory]:
    """Retrieves inventory positions for a product by its catalog ID."""
    statement = select(WarehouseInventory).where(WarehouseInventory.product_id == product_id)
    return session.exec(statement).all()


def create_inventory_item_controller(
    data: WarehouseInventoryCreate,
    session: Session,
) -> WarehouseInventory:
    """Creates a new inventory entry for a warehouse."""
    item = WarehouseInventory.from_orm(data)
    item.last_updated = datetime.utcnow()
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def reserve_stock_controller(
    request: StockReserveRequest,
    session: Session,
) -> dict:
    """
    Reserves stock for an order from the warehouse with highest availability.
    """
    query = select(WarehouseInventory)
    if request.sku:
        query = query.where(WarehouseInventory.sku == request.sku)
    elif request.product_id:
        query = query.where(WarehouseInventory.product_id == request.product_id)
    else:
        return {
            "success": False,
            "message": "Either sku or product_id must be provided to reserve stock.",
        }

    items = session.exec(query).all()
    if not items:
        return {
            "success": False,
            "message": f"No warehouse inventory found for sku='{request.sku}' / product_id='{request.product_id}'.",
        }

    # Find the warehouse with enough available stock (stock_on_hand - stock_reserved >= quantity)
    for item in items:
        available = item.stock_on_hand - item.stock_reserved
        if available >= request.quantity:
            item.stock_reserved += request.quantity
            item.last_updated = datetime.utcnow()
            session.add(item)
            session.commit()
            session.refresh(item)
            return {
                "success": True,
                "message": f"Successfully reserved {request.quantity} units for order '{request.order_reference or 'N/A'}'.",
                "warehouse": item.warehouse,
                "location": item.location,
                "sku": item.sku,
                "product_id": item.product_id,
                "units_reserved": request.quantity,
                "stock_on_hand": item.stock_on_hand,
                "stock_reserved_total": item.stock_reserved,
                "available_to_sell": item.stock_on_hand - item.stock_reserved,
            }

    total_avail = sum(i.stock_on_hand - i.stock_reserved for i in items)
    return {
        "success": False,
        "message": f"Insufficient stock. Requested: {request.quantity}, Total Available across warehouses: {total_avail}.",
        "sku": request.sku,
        "product_id": request.product_id,
    }


def restock_inventory_controller(
    request: StockRestockRequest,
    session: Session,
) -> dict:
    """Restocks merchandise in a specified warehouse."""
    statement = (
        select(WarehouseInventory)
        .where(WarehouseInventory.sku == request.sku)
        .where(WarehouseInventory.warehouse == request.warehouse)
    )
    item = session.exec(statement).first()

    if item:
        item.stock_on_hand += request.quantity
        if request.location:
            item.location = request.location
        item.last_updated = datetime.utcnow()
        session.add(item)
        session.commit()
        session.refresh(item)
        return {
            "success": True,
            "message": f"Restocked {request.quantity} units in {item.warehouse}.",
            "sku": item.sku,
            "product_id": item.product_id,
            "new_stock_on_hand": item.stock_on_hand,
            "location": item.location,
        }
    else:
        return {
            "success": False,
            "message": f"Inventory record not found for SKU '{request.sku}' in '{request.warehouse}'. Create the item first.",
        }


def get_low_stock_alerts_controller(
    session: Session,
) -> List[LowStockAlert]:
    """Identifies all products whose available stock is below or equal to the reorder threshold."""
    items = session.exec(select(WarehouseInventory)).all()
    alerts = []
    for item in items:
        avail = item.stock_on_hand - item.stock_reserved
        if avail <= item.reorder_threshold:
            status_desc = "OUT_OF_STOCK" if avail <= 0 else "CRITICAL_LOW_STOCK"
            alerts.append(
                LowStockAlert(
                    product_id=item.product_id,
                    sku=item.sku,
                    product_name=item.product_name,
                    warehouse=item.warehouse,
                    location=item.location,
                    stock_on_hand=item.stock_on_hand,
                    stock_reserved=item.stock_reserved,
                    available_to_sell=avail,
                    reorder_threshold=item.reorder_threshold,
                    alert_status=status_desc,
                )
            )
    return alerts
