import time
import random
import requests
import os

WEBHOOK_URL = "http://localhost:8000/webhook/logs"

LOGS = [
    "2026-05-10 09:00:01 INFO  [AuthService] User session initialized for user_id=1024",
    "2026-05-10 09:00:03 INFO  [Gateway] Incoming request GET /api/dashboard",
    "2026-05-10 09:00:04 INFO  [DBPool] Connection acquired pool_size=12 active=3",
    "2026-05-10 09:00:05 INFO  [Cache] Cache hit for key=user_profile_1024",
    "2026-05-10 09:00:07 INFO  [NotificationService] Email queued to user1024@example.com",
    "2026-05-10 09:00:09 INFO  [Analytics] Event processed event=dashboard_view",
    "2026-05-10 09:00:10 INFO  [Scheduler] Background cleanup task completed",
    "2026-05-10 09:00:11 INFO  [PaymentService] Payment verification successful txn_id=TX8831",
    "2026-05-10 09:00:13 INFO  [SearchService] Search query executed latency=42ms",
    "2026-05-10 09:00:15 INFO  [InventoryService] Inventory sync completed",
    "2026-05-10 09:00:18 ERROR [DBService] Query timeout while fetching orders query_id=Q8821",
    "2026-05-10 09:00:20 INFO  [Gateway] Incoming request POST /api/orders",
    "2026-05-10 09:00:21 INFO  [OrderService] Order created successfully order_id=ORD9011",
    "2026-05-10 09:00:23 INFO  [Cache] Cache refreshed for key=inventory_items",
    "2026-05-10 09:00:24 INFO  [AuthService] Token refreshed for user_id=882",
    "2026-05-10 09:00:25 INFO  [Analytics] Event processed event=checkout_start",
    "2026-05-10 09:00:27 INFO  [NotificationService] SMS notification delivered",
    "2026-05-10 09:00:29 INFO  [Gateway] Health check passed status=200",
    "2026-05-10 09:00:30 INFO  [Scheduler] Cron job executed job=invoice_cleanup",
    "2026-05-10 09:00:32 INFO  [DBPool] Connection released active=2",
    "2026-05-10 09:00:34 INFO  [SearchService] Indexed 450 new records",
    "2026-05-10 09:00:36 WARN  [Cache] Slow cache response latency=510ms",
    "2026-05-10 09:00:38 ERROR [AuthService] Failed login attempt user_id=991 reason=invalid_password",
    "2026-05-10 09:00:40 INFO  [Gateway] Incoming request GET /api/products",
    "2026-05-10 09:00:42 INFO  [ProductService] Product list fetched count=28",
    "2026-05-10 09:00:43 INFO  [InventoryService] Stock validation completed",
    "2026-05-10 09:00:45 INFO  [Cache] Cache hit for key=top_products",
    "2026-05-10 09:00:47 INFO  [Analytics] Event processed event=product_click",
    "2026-05-10 09:00:48 INFO  [DBPool] Connection acquired pool_size=12 active=4",
    "2026-05-10 09:00:50 INFO  [Scheduler] Backup task scheduled",
    "2026-05-10 09:00:51 INFO  [NotificationService] Push notification sent",
    "2026-05-10 09:00:53 INFO  [PaymentService] Refund processed txn_id=RF8812",
    "2026-05-10 09:00:55 INFO  [Gateway] Request completed status=200 latency=81ms",
    "2026-05-10 09:00:57 ERROR [PaymentService] Payment gateway unreachable provider=Stripe",
    "2026-05-10 09:01:00 INFO  [Gateway] Incoming request GET /api/users",
    "2026-05-10 09:01:02 INFO  [UserService] User profile fetched user_id=1024",
    "2026-05-10 09:01:03 INFO  [Cache] Cache hit for key=user_preferences",
    "2026-05-10 09:01:05 INFO  [Analytics] Event processed event=settings_open",
    "2026-05-10 09:01:07 INFO  [Scheduler] Metrics aggregation completed",
    "2026-05-10 09:01:09 INFO  [Gateway] Health check passed status=200",
    "2026-05-10 09:01:11 INFO  [DBPool] Connection released active=1",
    "2026-05-10 09:01:12 INFO  [NotificationService] Email delivery confirmed",
    "2026-05-10 09:01:14 INFO  [SearchService] Query executed latency=31ms",
    "2026-05-10 09:01:16 WARN  [Gateway] High response latency endpoint=/api/users latency=910ms",
    "2026-05-10 09:01:18 ERROR [InventoryService] Stock mismatch detected sku=SKU9912",
    "2026-05-10 09:01:20 INFO  [Gateway] Incoming request POST /api/cart",
    "2026-05-10 09:01:22 INFO  [CartService] Item added to cart item_id=IT991",
    "2026-05-10 09:01:24 INFO  [Analytics] Event processed event=add_to_cart",
    "2026-05-10 09:01:26 INFO  [Cache] Cache refreshed key=cart_1024",
    "2026-05-10 09:01:28 INFO  [DBService] Query executed rows=12 latency=18ms",
    "2026-05-10 09:01:29 INFO  [Scheduler] Temporary files cleaned",
    "2026-05-10 09:01:31 INFO  [Gateway] Request completed status=201 latency=76ms",
    "2026-05-10 09:01:33 INFO  [PaymentService] Payment authorized txn_id=TX9912",
    "2026-05-10 09:01:35 INFO  [NotificationService] SMS delivery confirmed",
    "2026-05-10 09:01:37 INFO  [AuthService] Session validated user_id=556",
    "2026-05-10 09:01:39 ERROR [SearchService] Elasticsearch cluster unavailable node=es-node-2",
    "2026-05-10 09:01:41 INFO  [Gateway] Incoming request GET /api/orders",
    "2026-05-10 09:01:42 INFO  [OrderService] Orders fetched count=16",
    "2026-05-10 09:01:44 INFO  [Cache] Cache hit key=recent_orders",
    "2026-05-10 09:01:46 INFO  [Analytics] Event processed event=orders_view",
    "2026-05-10 09:01:47 INFO  [Gateway] Request completed status=200 latency=69ms",
    "2026-05-10 09:01:49 INFO  [DBPool] Connection acquired pool_size=12 active=5",
    "2026-05-10 09:01:51 INFO  [Scheduler] Daily report generation started",
    "2026-05-10 09:01:52 INFO  [NotificationService] Push notification queued",
    "2026-05-10 09:01:54 INFO  [ProductService] Product recommendation generated",
    "2026-05-10 09:01:56 INFO  [Gateway] Health check passed status=200",
    "2026-05-10 09:01:58 WARN  [Cache] Redis memory usage high usage=88%",
    "2026-05-10 09:02:00 ERROR [DBService] Deadlock detected transaction_id=TXN7782",
    "2026-05-10 09:02:02 INFO  [Gateway] Incoming request PUT /api/profile",
    "2026-05-10 09:02:04 INFO  [UserService] Profile updated successfully user_id=1024",
    "2026-05-10 09:02:05 INFO  [Analytics] Event processed event=profile_update",
    "2026-05-10 09:02:07 INFO  [NotificationService] Confirmation email sent",
    "2026-05-10 09:02:09 INFO  [Cache] Cache invalidated key=user_profile_1024",
    "2026-05-10 09:02:10 INFO  [Scheduler] Session cleanup completed",
    "2026-05-10 09:02:12 INFO  [Gateway] Request completed status=200 latency=92ms",
    "2026-05-10 09:02:14 INFO  [DBPool] Connection released active=3",
    "2026-05-10 09:02:15 INFO  [SearchService] Search index updated",
    "2026-05-10 09:02:17 INFO  [PaymentService] Invoice generated invoice_id=INV8821",
    "2026-05-10 09:02:19 ERROR [NotificationService] SMTP server timeout host=smtp.mail.local",
    "2026-05-10 09:02:21 INFO  [Gateway] Incoming request GET /api/metrics",
    "2026-05-10 09:02:23 INFO  [MetricsService] Metrics aggregation completed",
    "2026-05-10 09:02:24 INFO  [Analytics] Event processed event=metrics_view",
    "2026-05-10 09:02:26 INFO  [Cache] Cache hit key=system_metrics",
    "2026-05-10 09:02:28 INFO  [DBService] Query executed rows=120 latency=44ms",
    "2026-05-10 09:02:30 INFO  [Gateway] Health check passed status=200",
    "2026-05-10 09:02:31 INFO  [Scheduler] Backup completed successfully",
    "2026-05-10 09:02:33 INFO  [AuthService] User logout successful user_id=882",
    "2026-05-10 09:02:35 INFO  [NotificationService] Webhook delivered",
    "2026-05-10 09:02:37 WARN  [Gateway] Retry triggered for upstream request",
    "2026-05-10 09:02:39 ERROR [Gateway] Upstream service unavailable service=RecommendationAPI",
    "2026-05-10 09:02:41 INFO  [Gateway] Incoming request GET /api/reports",
    "2026-05-10 09:02:42 INFO  [ReportService] Report generated report_id=RPT102",
    "2026-05-10 09:02:44 INFO  [Analytics] Event processed event=report_download",
    "2026-05-10 09:02:46 INFO  [Cache] Cache refreshed key=monthly_reports",
    "2026-05-10 09:02:47 INFO  [DBPool] Connection acquired pool_size=12 active=2",
    "2026-05-10 09:02:49 INFO  [SearchService] Query executed latency=27ms",
    "2026-05-10 09:02:51 INFO  [Gateway] Request completed status=200 latency=73ms",
    "2026-05-10 09:02:53 INFO  [NotificationService] Push notification delivered",
    "2026-05-10 09:02:55 INFO  [Scheduler] Archival task completed",
    "2026-05-10 09:02:57 INFO  [PaymentService] Settlement completed batch_id=BAT771",
    "2026-05-10 09:02:59 ERROR [Cache] Redis connection lost node=redis-primary",
    "2026-05-10 09:03:01 INFO  [Gateway] Incoming request GET /api/status",
    "2026-05-10 09:03:03 INFO  [SystemService] System status fetched",
    "2026-05-10 09:03:04 INFO  [Analytics] Event processed event=status_check",
    "2026-05-10 09:03:06 INFO  [DBService] Query executed rows=4 latency=11ms",
    "2026-05-10 09:03:08 INFO  [Gateway] Health check passed status=200",
    "2026-05-10 09:03:10 INFO  [NotificationService] Alert email queued",
    "2026-05-10 09:03:12 INFO  [Scheduler] Resource cleanup completed",
    "2026-05-10 09:03:13 INFO  [AuthService] MFA verification successful user_id=772",
    "2026-05-10 09:03:15 INFO  [Gateway] Request completed status=200 latency=64ms",
    "2026-05-10 09:03:17 WARN  [InventoryService] Low stock detected sku=SKU7712 remaining=4",
    "2026-05-10 09:03:19 ERROR [OrderService] Failed to update order status order_id=ORD8821",
    "2026-05-10 09:03:21 INFO  [Gateway] Incoming request DELETE /api/cart",
    "2026-05-10 09:03:23 INFO  [CartService] Cart cleared successfully user_id=1024",
    "2026-05-10 09:03:25 INFO  [Analytics] Event processed event=cart_clear",
    "2026-05-10 09:03:26 INFO  [Cache] Cache invalidated key=cart_1024",
    "2026-05-10 09:03:28 INFO  [Gateway] Request completed status=204 latency=48ms",
]


while True:

    log = random.choice(LOGS)

    try:

        response = requests.post(
            WEBHOOK_URL,
            json={
                "raw_logs": log
            },
            timeout=120,
        )

        print("=" * 60)
        print("✅ Sent log")
        print("Status:", response.status_code)

        try:
            print(response.json())
        except:
            print(response.text)

    except Exception as e:
        print("❌ Error:", e)

    # Wait before next log
    time.sleep(2)