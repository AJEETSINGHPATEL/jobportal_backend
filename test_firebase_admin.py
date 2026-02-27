import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

def test_firebase():
    print("Testing Firebase Admin Initialization...")
    project_id = os.getenv("FIREBASE_PROJECT_ID", "portal-31935")
    print(f"Project ID: {project_id}")
    
    try:
        if not firebase_admin._apps:
            # Try initializing with just project id if service account is missing
            service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "service-account.json")
            if os.path.exists(service_account_path):
                print(f"Found service account at {service_account_path}")
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
            else:
                print("Service account file not found. Trying default initialization with Project ID...")
                firebase_admin.initialize_app(options={'projectId': project_id})
        
        db = firestore.client()
        print("Success: Firestore client created.")
        
        # Try a simple write
        print("Testing write to 'test_migration' collection...")
        doc_ref = db.collection("test_migration").document("status")
        doc_ref.set({"migrated": True, "time": firestore.SERVER_TIMESTAMP})
        print("Success: Document written.")
        
        # Try a simple read
        doc = doc_ref.get()
        print(f"Success: Document read back: {doc.to_dict()}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_firebase()
