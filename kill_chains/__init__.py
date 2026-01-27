from kill_chains.upi_fraud import UPIFraudKillChain
from kill_chains.account_takeover import AccountTakeoverKillChain

KILL_CHAIN_MAP = {
    "UPI_FRAUD": UPIFraudKillChain,
    "ACCOUNT_TAKEOVER": AccountTakeoverKillChain
}

def get_kill_chain(scam_type: str):
    """
    Factory function to instantiate correct kill-chain.
    """
    if scam_type not in KILL_CHAIN_MAP:
        # Default to UPI fraud if unknown type
        scam_type = "UPI_FRAUD"
    
    return KILL_CHAIN_MAP[scam_type]()
