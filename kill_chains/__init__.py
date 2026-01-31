from typing import Any, Optional

from kill_chains.base_kill_chain import BaseKillChain
from kill_chains.upi_fraud import UPIFraudKillChain
from kill_chains.account_takeover import AccountTakeoverKillChain
from kill_chains.fake_support import FakeCustomerSupportKillChain
from kill_chains.phishing import PhishingKillChain
from kill_chains.investment_scam import InvestmentScamKillChain
from kill_chains.fake_offer import FakeOfferKillChain

KILL_CHAIN_MAP = {
    "UPI_FRAUD": UPIFraudKillChain,
    "ACCOUNT_TAKEOVER": AccountTakeoverKillChain,
    "FAKE_CUSTOMER_SUPPORT": FakeCustomerSupportKillChain,
    "PHISHING": PhishingKillChain,
    "INVESTMENT_SCAM": InvestmentScamKillChain,
    "FAKE_OFFER": FakeOfferKillChain,
}


def get_kill_chain(scam_type: str, llm_client: Optional[Any] = None) -> BaseKillChain:
    """
    Factory: instantiate kill-chain for scam type.
    Pass llm_client (e.g. from utils.llm_client.LLMClient.create) for Phase 3 FIX 9 LLM fallback.
    """
    if scam_type not in KILL_CHAIN_MAP:
        scam_type = "UPI_FRAUD"
    return KILL_CHAIN_MAP[scam_type](llm_client=llm_client)
