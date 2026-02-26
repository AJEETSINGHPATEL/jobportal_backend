from app.routers.ai import chat_with_ai
import inspect
from fastapi.dependencies.utils import get_typed_signature

sig = get_typed_signature(chat_with_ai)
print("Signature:", sig)
for name, param in sig.parameters.items():
    print(f"Param: {name}, Default: {param.default}")

from app.utils.auth import get_optional_user
sig_opt = get_typed_signature(get_optional_user)
print("\nget_optional_user Signature:", sig_opt)
for name, param in sig_opt.parameters.items():
    print(f"Param: {name}, Default: {param.default}")

from app.utils.auth import optional_security
print("\noptional_security type:", type(optional_security))
