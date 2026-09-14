from dataclasses import asdict, dataclass
import os


@dataclass(frozen=True)
class CompanyProfile:
    deployment_mode: str = "local_windows"
    communication_provider: str = "chatgpt_gmail"
    legal_status: str = "unregistered"
    invoice_mode: str = "draft_only"
    automatic_sending: bool = False

    def to_dict(self) -> dict:
        data = asdict(self)
        data["limitations"] = [
            "ChatGPT Gmail creates drafts only after operator approval",
            "No official tax invoices while legal_status is unregistered",
            "No public production deployment in local_windows mode",
        ]
        return data


def current_profile() -> CompanyProfile:
    return CompanyProfile(
        deployment_mode=os.getenv("DEPLOYMENT_MODE", "local_windows"),
        communication_provider=os.getenv("COMMUNICATION_PROVIDER", "chatgpt_gmail"),
        legal_status=os.getenv("LEGAL_STATUS", "unregistered"),
    )
