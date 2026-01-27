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
    "FAKE_OFFER": FakeOfferKillChain
}

def get_kill_chain(scam_type: str):
    """
    Factory function to instantiate correct kill-chain.
    Returns kill-chain instance for given scam type.
    """
    if scam_type not in KILL_CHAIN_MAP:
        # Default to UPI fraud if unknown type
        scam_type = "UPI_FRAUD"
    
    return KILL_CHAIN_MAP[scam_type]()
