import sys
sys.path.append('.')
from agent.policy import handle_attach_to, handle_to_hand, AreaType
from agent.policy import LILLIE_CLEFAIRY_EX, ALAKAZAM, PSYCHIC_ENERGY, DUNSPARCE, DUDUNSPARCE

class DummyOption:
    def __init__(self, index, inPlayArea=AreaType.BENCH):
        self.index = index
        self.inPlayArea = inPlayArea
        self.area = inPlayArea

class DummyCard:
    def __init__(self, id, energies=None):
        self.id = id
        self.energies = energies or []

class DummyPlayer:
    def __init__(self):
        self.deckCount = 10
        self.active = [None]
        self.bench = [None] * 5

class DummyState:
    def __init__(self):
        self.yourIndex = 0
        self.players = [DummyPlayer(), DummyPlayer()]

class DummySelect:
    def __init__(self, energy_id):
        self.contextCard = DummyCard(energy_id)

class DummyObs:
    def __init__(self, state, energy_id=None):
        self.current = state
        self.select = DummySelect(energy_id) if energy_id else None

def test_clefairy_energy():
    print("=== Testing Clefairy Energy Attachment Priority ===")
    state = DummyState()
    # Clefairy is active
    state.players[0].active[0] = DummyCard(LILLIE_CLEFAIRY_EX)
    # Alakazam is bench (index 0)
    state.players[0].bench[0] = DummyCard(ALAKAZAM, energies=[1])
    
    obs = DummyObs(state, energy_id=PSYCHIC_ENERGY)
    options = [
        DummyOption(index=0, inPlayArea=AreaType.ACTIVE), # Clefairy
        DummyOption(index=0, inPlayArea=AreaType.BENCH),  # Alakazam
    ]
    
    scores = handle_attach_to(obs, options, 1, 1)
    print("Scores for [Clefairy Active, Alakazam Bench(1 energy)]:")
    print("Options passed to _pick_best:")
    # We can't see the internal scores easily without patching, but we know _pick_best returns a list of selected indices.
    # Actually, we can just call the logic block directly or print what it returns.
    print(scores)

def test_pokedex_pull():
    print("\n=== Testing Deck Search Priority (Dunsparce vs Dudunsparce) ===")
    state = DummyState()
    # field has NO Dunsparce
    obs = DummyObs(state)
    options = [
        DummyOption(index=0, inPlayArea=AreaType.DECK), # Dunsparce
        DummyOption(index=1, inPlayArea=AreaType.DECK), # Dudunsparce
    ]
    # We need to mock _get_card for handle_to_hand
    # Wait, handle_to_hand uses _get_card, which reads from the area. DECK cards aren't easily mocked unless we patch _get_card.
    pass

if __name__ == '__main__':
    test_clefairy_energy()
