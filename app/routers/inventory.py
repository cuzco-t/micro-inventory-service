"""
Inventory routes: API endpoints for warehouse stock inquiries, reservations, restocks and alerts.
"""

import logging
from typing import Annotated, List, Optional
from fastapi import APIRouter, Query, status

from ..controllers.inventory import (
    create_inventory_item_controller,
    get_all_inventory_controller,
    get_inventory_by_product_id_controller,
    get_inventory_by_sku_controller,
    get_low_stock_alerts_controller,
    reserve_stock_controller,
    restock_inventory_controller,
)
from ..core import SessionDep
from ..models.inventory import (
    LowStockAlert,
    StockReserveRequest,
    StockRestockRequest,
    WarehouseInventory,
    WarehouseInventoryCreate,
)

router = APIRouter(prefix="/inventory", tags=["Warehouse Inventory"])
logger = logging.getLogger(__name__)


@router.get(
    "/",
    response_model=List[WarehouseInventory],
    summary="List warehouse stock across all distribution centers",
)
def get_all_inventory_router(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
    warehouse: Optional[str] = None,
):
    """
    Returns inventory details including warehouse name, physical shelf location,
    stock on hand, and reserved stock.
    """
    return get_all_inventory_controller(session, offset, limit, warehouse)


@router.get(
    "/sku/{sku}",
    response_model=List[WarehouseInventory],
    summary="Get stock availability and physical location by SKU",
)
def get_inventory_by_sku_router(sku: str, session: SessionDep):
    """
    Inquires real-time stock levels, warehouse locations (e.g. Pasillo A-12),
    and available quantity for a specific product SKU.
    """
    return get_inventory_by_sku_controller(sku, session)


@router.get(
    "/product/{product_id}",
    response_model=List[WarehouseInventory],
    summary="Get stock availability and physical location by Product ID",
)
def get_inventory_by_product_id_router(product_id: int, session: SessionDep):
    """
    Inquires real-time warehouse stock and physical locations using the catalog product ID.
    """
    return get_inventory_by_product_id_controller(product_id, session)


@router.post(
    "/reserve",
    summary="Reserve warehouse stock for a customer order",
)
def reserve_stock_router(request: StockReserveRequest, session: SessionDep):
    """
    Reserves requested units from the warehouse with sufficient stock.
    Prevents overselling when an order is being finalized.
    """
    return reserve_stock_controller(request, session)


@router.post(
    "/restock",
    summary="Restock merchandise inventory in a warehouse",
)
def restock_inventory_router(request: StockRestockRequest, session: SessionDep):
    """
    Increases physical stock in a specified warehouse when a supplier shipment arrives.
    """
    return restock_inventory_controller(request, session)


@router.get(
    "/alerts/low-stock",
    response_model=List[LowStockAlert],
    summary="Get low-stock or out-of-stock items needing reordering",
)
def get_low_stock_alerts_router(session: SessionDep):
    """
    Reports all inventory items whose available stock has fallen below their reorder threshold.
    """
    return get_low_stock_alerts_controller(session)


@router.post(
    "/",
    response_model=WarehouseInventory,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new warehouse inventory record",
)
def create_inventory_item_router(
    data: WarehouseInventoryCreate, session: SessionDep
):
    """
    Adds a new product SKU into a warehouse distribution center.
    """
    return create_inventory_item_controller(data, session)
