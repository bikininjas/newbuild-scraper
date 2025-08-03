import os
WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def send_discord_alert(product_name, url, old_price, new_price):
    percent_drop = ((old_price - new_price) / old_price) * 100 if old_price else 0
    print("\n==============================")
    print("🔔 Price drop detected!")
    print(f"Product: {product_name}")
    print(f"Old price: {old_price}€")
    print(f"New price: {new_price}€")
    print(f"Drop: {percent_drop:.2f}%")
    print(f"Product page: {url}")
    print("==============================\n")
