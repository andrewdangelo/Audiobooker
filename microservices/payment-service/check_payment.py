"""
Manually process payment and add credits
This simulates what the Stripe webhook would do
"""
import requests
import json

# Your user ID from the console
USER_ID = "697cff8c537e94a7b0dc3047"

# Check recent payment to get details
print("Fetching recent payment...")
response = requests.get(f"http://localhost:8000/payment/user/{USER_ID}/payments")

if response.status_code == 200:
    data = response.json()
    payments = data.get('payments', [])
    
    if payments:
        payment = payments[0]  # Most recent
        print(f"\nPayment found:")
        print(f"  Amount: ${payment.get('amount', 0) / 100:.2f}")
        print(f"  Status: {payment.get('status')}")
        
        metadata = payment.get('metadata', {})
        credits = metadata.get('credits')
        credit_type = metadata.get('credit_type', 'basic')
        
        if credits:
            print(f"  Credits: {credits}")
            print(f"  Type: {credit_type}")
            
            # Now manually update the user's credits via auth service
            print(f"\nAdding {credits} {credit_type} credits to user...")
            
            # You'll need to do this directly in MongoDB or create an endpoint
            print("\n⚠️  Webhook wasn't triggered automatically.")
            print("To add credits manually, run this in your MongoDB shell or use MongoDB Compass:")
            print(f"""
db.users.updateOne(
  {{ _id: ObjectId("{USER_ID}") }},
  {{ 
    $inc: {{ 
      {"premium_credits" if credit_type == "premium" else "basic_credits"}: {credits},
      credits: {credits}
    }},
    $set: {{ updated_at: new Date() }}
  }}
)
""")
        else:
            print("  ❌ No credits in metadata!")
            print(f"  Metadata: {json.dumps(metadata, indent=2)}")
    else:
        print("❌ No payments found")
else:
    print(f"❌ Error fetching payments: {response.status_code}")
    print(response.text)
