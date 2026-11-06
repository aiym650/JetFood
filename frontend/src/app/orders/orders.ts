import { ChangeDetectorRef, Component, DestroyRef, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DeliveryRoute, Orders as OrdersService } from '../orders';
import { OrderRecord } from '../orders';
import { Auth } from '../auth';
import { ActivatedRoute, Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { timeout, timer } from 'rxjs';
import { I18nService } from '../i18n/i18n.service';
import { Menu, FoodItem } from '../menu';

interface EditableOrderItem {
  item_id: number | null;
  item_name: string;
  quantity: number;
  price: number;
}

@Component({
  selector: 'app-orders',
  imports: [CommonModule],
  templateUrl: './orders.html',
  styleUrl: './orders.css',
})
export class OrdersPage implements OnInit {
  orders: OrderRecord[] = [];
  loading = true;
  refreshing = false;
  error = '';
  refreshError = '';
  currentUser: any = null;
  cancellingOrderId: number | null = null;
  editingOrderId: number | null = null;
  savingEdit = false;
  editError = '';
  editSuccess = '';
  editAddress = '';
  editNotes = '';
  editItems: EditableOrderItem[] = [];
  availableMenuItems: FoodItem[] = [];
  itemsChanged = false;
  deliveryRoutes: Record<number, DeliveryRoute | null> = {};
  routeLoadErrors: Record<number, string> = {};
  routeLoading = false;
  routeEditingOrderId: number | null = null;
  routeOriginAddress = '';
  routeNotes = '';
  savingRoute = false;
  routeSaveError = '';
  confirmingDeliveryOrderId: number | null = null;
  deliveryConfirmationError = '';

  get editItemCount(): number {
    return this.editItems.reduce((sum, item) => sum + item.quantity, 0);
  }

  get editTotal(): number {
    return this.editItems.reduce((sum, item) => sum + item.quantity * item.price, 0);
  }
  expandedOrderId: number | null = null;

  constructor(
    private ordersService: OrdersService,
    private menuService: Menu,
    private auth: Auth,
    private router: Router,
    private route: ActivatedRoute,
    private changeDetector: ChangeDetectorRef,
    private destroyRef: DestroyRef,
    public i18n: I18nService
  ) {
    this.i18n.currentLang$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.changeDetector.markForCheck());
  }

  ngOnInit(): void {
    this.currentUser = this.auth.getCurrentUser();
    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const orderId = Number(params.get('orderId'));
        if (Number.isSafeInteger(orderId) && orderId > 0) {
          this.expandedOrderId = orderId;
          if (this.auth.isLoggedIn()) {
            this.loadDeliveryRoute(orderId);
          }
          this.changeDetector.markForCheck();
        }
      });

    if (!this.auth.isLoggedIn()) {
      this.router.navigate(['/landing']);
      return;
    }

    this.loadOrders();
    timer(30_000, 30_000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (this.hasActiveOrders && !this.loading && !this.refreshing && this.cancellingOrderId === null) {
          this.refreshOrders();
        }
      });
  }

  get hasActiveOrders(): boolean {
    return this.orders.some((order) => !['delivered', 'cancelled'].includes(order.status));
  }

  loadOrders(): void {
    this.loading = true;
    this.error = '';
    this.ordersService.getOrders().pipe(
      timeout({ first: 12000 }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (data) => {
        this.orders = data;
        this.loading = false;
        this.changeDetector.markForCheck();
      },
      error: (err) => {
        console.error('Error loading orders:', err);
        this.error = this.i18n.t('ordersLoadFailed');
        this.loading = false;
        this.changeDetector.markForCheck();
      }
    });
  }

  refreshOrders(): void {
    if (this.loading || this.refreshing) {
      return;
    }

    this.refreshing = true;
    this.refreshError = '';
    this.ordersService.getOrders().pipe(
      timeout({ first: 12000 }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (data) => {
        this.orders = data;
        this.refreshing = false;
        this.changeDetector.markForCheck();
      },
      error: (error) => {
        console.error('Error refreshing orders:', error);
        this.refreshError = this.i18n.t('refreshFailed');
        this.refreshing = false;
        this.changeDetector.markForCheck();
      }
    });
  }

  statusLabel(status: string): string {
    const key = `orderStatuses.${status}`;
    const label = this.i18n.t(key);
    return label === key ? status : label;
  }

  retryOrders(): void {
    if (this.error) {
      this.loadOrders();
      return;
    }
    this.refreshOrders();
  }

  toggleOrderDetails(orderId: number): void {
    this.expandedOrderId = this.expandedOrderId === orderId ? null : orderId;
    if (this.expandedOrderId === orderId) {
      this.loadDeliveryRoute(orderId);
    }
  }

  canManageRoute(order: OrderRecord): boolean {
    return this.currentUser?.role === 'admin'
      || this.currentUser?.role === 'manager'
      || (this.currentUser?.role === 'delivery' && order.delivery_person === this.currentUser?.id);
  }

  private loadDeliveryRoute(orderId: number): void {
    if (Object.prototype.hasOwnProperty.call(this.deliveryRoutes, orderId) || this.routeLoadErrors[orderId]) {
      return;
    }
    this.routeLoading = true;
    this.ordersService.getDeliveryRoute(orderId).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (route) => {
        this.deliveryRoutes[orderId] = route;
        this.routeLoading = false;
        this.changeDetector.markForCheck();
      },
      error: (error) => {
        if (error.status === 404) {
          this.deliveryRoutes[orderId] = null;
        } else {
          this.routeLoadErrors[orderId] = this.i18n.t('deliveryRouteLoadFailed');
        }
        this.routeLoading = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  beginRouteEdit(order: OrderRecord): void {
    this.routeEditingOrderId = order.id;
    this.routeOriginAddress = this.deliveryRoutes[order.id]?.origin_address ?? '';
    this.routeNotes = this.deliveryRoutes[order.id]?.notes ?? '';
    this.routeSaveError = '';
  }

  saveDeliveryRoute(orderId: number): void {
    if (!this.routeOriginAddress.trim()) {
      this.routeSaveError = this.i18n.t('deliveryRouteOriginRequired');
      return;
    }
    this.savingRoute = true;
    this.routeSaveError = '';
    this.ordersService.saveDeliveryRoute(orderId, {
      origin_address: this.routeOriginAddress.trim(),
      notes: this.routeNotes,
    }).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (route) => {
        this.deliveryRoutes[orderId] = route;
        this.routeEditingOrderId = null;
        this.savingRoute = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.routeSaveError = this.i18n.t('deliveryRouteSaveFailed');
        this.savingRoute = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  confirmDelivery(order: OrderRecord): void {
    this.confirmingDeliveryOrderId = order.id;
    this.deliveryConfirmationError = '';
    this.ordersService.confirmDelivery(order.id).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (result) => {
        this.orders = this.orders.map(current => current.id === order.id
          ? { ...current, delivery_confirmed_at: result.delivery_confirmed_at }
          : current);
        this.confirmingDeliveryOrderId = null;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.deliveryConfirmationError = this.i18n.t('deliveryConfirmationFailed');
        this.confirmingDeliveryOrderId = null;
        this.changeDetector.markForCheck();
      },
    });
  }

  cancelOrder(orderId: number): void {
    this.error = '';
    this.cancellingOrderId = orderId;
    this.ordersService.updateOrderStatus(orderId, 'cancelled').pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.cancellingOrderId = null;
        this.loadOrders();
      },
      error: () => {
        this.error = this.i18n.t('cancelOrderFailed');
        this.cancellingOrderId = null;
        this.changeDetector.markForCheck();
      },
    });
  }

  beginEditOrder(order: OrderRecord): void {
    this.editingOrderId = order.id;
    this.expandedOrderId = order.id;
    this.editAddress = order.delivery_address;
    this.editNotes = order.delivery_notes;
    this.editItems = order.items.map(item => ({
      item_id: item.menu_item_id,
      item_name: item.item_name,
      quantity: item.quantity,
      price: Number(item.price_per_item),
    }));
    this.itemsChanged = false;
    this.editError = '';
    this.editSuccess = '';
    this.menuService.getItems().subscribe({
      next: (items) => {
        this.availableMenuItems = items;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.editError = this.i18n.t('menuLoadFailed');
        this.changeDetector.markForCheck();
      },
    });
  }

  addEditMenuItem(value: string): void {
    const item = this.availableMenuItems.find(candidate => candidate.id === Number(value));
    if (!item) return;
    if (this.editItemCount >= 50) {
      this.editError = this.i18n.t('maxOrderItems');
      return;
    }

    const line = this.editItems.find(entry => entry.item_id === item.id);
    if (line) line.quantity += 1;
    else this.editItems.push({
      item_id: item.id,
      item_name: item.name,
      quantity: 1,
      price: Number(item.price),
    });
    this.itemsChanged = true;
    this.editError = '';
  }

  changeEditQuantity(index: number, change: number): void {
    const item = this.editItems[index];
    if (!item) return;
    const quantity = item.quantity + change;
    if (quantity > 50 || (change > 0 && this.editItemCount >= 50)) {
      this.editError = this.i18n.t('maxOrderItems');
      return;
    }
    if (quantity < 1) this.editItems.splice(index, 1);
    else item.quantity = quantity;
    this.itemsChanged = true;
    this.editError = '';
  }

  saveOrderEdit(orderId: number): void {
    this.editError = '';
    if (!this.editAddress.trim()) {
      this.editError = this.i18n.t('missingDeliveryAddress');
      return;
    }
    if (this.itemsChanged && (
      this.editItems.length === 0 || this.editItems.some(item => item.item_id === null)
    )) {
      this.editError = this.i18n.t('orderItemsUnavailable');
      return;
    }

    this.savingEdit = true;
    const changes: {
      delivery_address: string;
      delivery_notes: string;
      items?: { item_id: number; quantity: number }[];
    } = {
      delivery_address: this.editAddress.trim(),
      delivery_notes: this.editNotes,
    };
    if (this.itemsChanged) {
      changes.items = this.editItems.flatMap(item => item.item_id === null
        ? []
        : [{ item_id: item.item_id, quantity: item.quantity }]);
    }

    this.ordersService.modifyOrder(orderId, changes).subscribe({
      next: (updatedOrder) => {
        this.orders = this.orders.map(order => order.id === updatedOrder.id ? updatedOrder : order);
        this.editingOrderId = null;
        this.editSuccess = this.i18n.t('orderUpdated');
        this.savingEdit = false;
        this.changeDetector.markForCheck();
      },
      error: () => {
        this.editError = this.i18n.t('orderModifyFailed');
        this.savingEdit = false;
        this.changeDetector.markForCheck();
      },
    });
  }

  cancelEdit(): void {
    this.editingOrderId = null;
    this.editError = '';
    this.itemsChanged = false;
  }
}
