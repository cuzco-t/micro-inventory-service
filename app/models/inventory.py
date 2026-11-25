"""
Inventory models: SQLModel schemas and table definitions for warehouse stock management.
"""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class WarehouseInventoryBase(SQLModel):
    """
    Shared attributes for warehouse inventory.
    Links directly to catalog products via product_id and sku.
    """
    product_id: int = Field(
        index=True,
        description="Reference ID of the product in the product catalog service."
    )
    sku: str = Field(
        max_length=50,
        index=True,
        description="Global unique SKU matching the catalog product."
    )
    product_name: str = Field(
        max_length=150,
        description="Human-readable product reference name."
    )
    warehouse: str = Field(
        default="Almacén Central Lima",
        max_length=100,
        index=True,
        description="Name of the physical warehouse or distribution center."
    )
    location: str = Field(
        default="Pasillo General",
        max_length=100,
        description="Physical location inside the warehouse (e.g., Pasillo A-12, Estante 3)."
    )
    stock_on_hand: int = Field(
        default=0,
        ge=0,
        description="Physical quantity available in stock."
    )
    stock_reserved: int = Field(
        default=0,
        ge=0,
        description="Stock reserved for pending or processing customer orders."
    )
    reorder_threshold: int = Field(
        default=10,
        ge=0,
        description="Minimum stock quantity before generating a low-stock alert."
    )


class WarehouseInventory(WarehouseInventoryBase, table=True):
    """
    The Database Table Model for Warehouse Inventory.
    """
    __tablename__ = "warehouse_inventory"

    id: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="Internal primary key."
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the last inventory update."
    )


class WarehouseInventoryCreate(WarehouseInventoryBase):
    """Schema for registering a new inventory item."""
    pass


class WarehouseInventoryUpdate(SQLModel):
    """Schema for partial updates of inventory stock or location."""
    warehouse: Optional[str] = None
    location: Optional[str] = None
    stock_on_hand: Optional[int] = Field(default=None, ge=0)
    stock_reserved: Optional[int] = Field(default=None, ge=0)
    reorder_threshold: Optional[int] = Field(default=None, ge=0)


class StockReserveRequest(SQLModel):
    """Schema for reserving stock when a customer places an order."""
    sku: Optional[str] = Field(default=None, description="Product SKU to reserve.")
    product_id: Optional[int] = Field(default=None, description="Product ID to reserve.")
    quantity: int = Field(gt=0, description="Quantity of units to reserve.")
    order_reference: Optional[str] = Field(default=None, description="Associated order reference code.")


class StockRestockRequest(SQLModel):
    """Schema for restocking merchandise at a warehouse."""
    sku: str = Field(description="Product SKU to restock.")
    warehouse: str = Field(default="Almacén Central Lima", description="Warehouse name.")
    location: Optional[str] = Field(default=None, description="Shelf/bin location.")
    quantity: int = Field(gt=0, description="Quantity of new units received.")


class LowStockAlert(SQLModel):
    """Schema representing an alert for low stock items."""
    product_id: int
    sku: str
    product_name: str
    warehouse: str
    location: str
    stock_on_hand: int
    stock_reserved: int
    available_to_sell: int
    reorder_threshold: int
    alert_status: str
