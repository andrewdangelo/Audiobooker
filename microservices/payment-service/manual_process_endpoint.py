"""
Manual endpoint to process payments and add credits
Add this to your payment router temporarily for testing
"""
from fastapi import APIRouter, HTTPException
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/admin/process-payment/{payment_id}")
async def manually_process_payment(payment_id: str):
    """Manually process a payment and add credits (for testing when webhooks don't fire)"""
    try:
        from app.database.mongodb import MongoDB
        
        # Get payment
        payment = await MongoDB.get_db().payments.find_one({"_id": ObjectId(payment_id)})
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Check if this is a credit purchase
        metadata = payment.get("metadata", {})
        purchase_type = metadata.get("purchase_type")
        
        if purchase_type != "credits":
            return {"message": "Not a credit purchase", "payment_id": payment_id}
        
        credits_to_add = int(metadata.get("credits", 0))
        credit_type = metadata.get("credit_type", "basic")
        user_id = payment.get("user_id")
        
        if credits_to_add <= 0:
            raise HTTPException(status_code=400, detail="No credits to add")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="No user_id in payment")
        
        # Determine which credit field to update
        credit_field = "premium_credits" if credit_type == "premium" else "basic_credits"
        
        # Add credits to user
        result = await MongoDB.get_auth_db().users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$inc": {
                    credit_field: credits_to_add,
                    "credits": credits_to_add  # Legacy total
                },
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Manually added {credits_to_add} {credit_type} credits to user {user_id}")
            return {
                "status": "success",
                "message": f"Added {credits_to_add} {credit_type} credits to user",
                "user_id": user_id,
                "credits_added": credits_to_add,
                "credit_type": credit_type
            }
        else:
            raise HTTPException(status_code=404, detail="User not found")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
