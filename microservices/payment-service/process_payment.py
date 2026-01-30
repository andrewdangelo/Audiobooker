"""
Trigger manual credit processing for a user's most recent payment
"""
import requests

USER_ID = "697cff8c537e94a7b0dc3047"

# Get recent payment
print("Fetching recent payment...")
response = requests.get(f"http://localhost:8000/payment/user/{USER_ID}/payments")

if response.status_code == 200:
    data = response.json()
    payments = data.get('payments', [])
    
    if payments:
        payment = payments[0]  # Most recent
        payment_id = payment.get('payment_id') or payment.get('_id')
        
        if not payment_id:
            print(f"❌ Payment ID is missing from payment: {payment}")
            exit(1)
        
        print(f"Processing payment {payment_id}...")
        print(f"Payment details: Amount=${payment.get('amount', 0)/100:.2f}, Status={payment.get('status')}")
        
        # Trigger manual processing
        process_response = requests.post(f"http://localhost:8000/payment/admin/process-payment/{payment_id}")
        
        if process_response.status_code == 200:
            result = process_response.json()
            print(f"\n✅ Success!")
            print(f"   {result.get('message')}")
            print(f"   Credits added: {result.get('credits_added')}")
            print(f"   Credit type: {result.get('credit_type')}")
        else:
            print(f"\n❌ Error: {process_response.status_code}")
            print(process_response.text)
    else:
        print("❌ No payments found")
else:
    print(f"❌ Error fetching payments: {response.status_code}")
