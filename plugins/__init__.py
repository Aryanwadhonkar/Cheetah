# Credit protection at package level
from config import Config

def _verify_package_credits():
    required_credits = [
        "@wleaksOwner",
        "Aryanwadhonkar/Cheetah"
    ]
    for credit in required_credits:
        if credit not in Config.CREDIT:
            raise ImportError("Package credit verification failed")

_verify_package_credits()
