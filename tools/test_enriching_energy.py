import sys
import os
sys.path.insert(0, os.path.abspath('agent'))
from policy import handle_attach_to, ENRICHING_ENERGY, DUNSPARCE
from cg.api import Observation, SelectContext, AreaType

# Mock state
obs = type('obj', (object,), {
    'current': type('obj', (object,), {
        'yourIndex': 0,
        'players': [type('obj', (object,), {
            'deckCount': 4,
            'bench': []
        }), type('obj', (object,), {})]
    }),
    'select': type('obj', (object,), {
        'context': SelectContext.MAIN
    })
})

# Mock Option
options = [
    type('obj', (object,), {
        'area': AreaType.BENCH,
        'index': 0
    })
]

# Mock _get_card
def mock_get_card(obs, area, index, my_idx):
    return type('obj', (object,), {'id': DUNSPARCE, 'skills': []})
import policy
policy._get_card = mock_get_card
policy._energy_count = lambda x: 0
policy._hp_remaining = lambda x: 60

scores = handle_attach_to(obs, options, ENRICHING_ENERGY, 0)
print(f"Deck count 4 Enriching Energy -> score: {scores[0]}")

obs.current.players[0].deckCount = 5
scores = handle_attach_to(obs, options, ENRICHING_ENERGY, 0)
print(f"Deck count 5 Enriching Energy -> score: {scores[0]}")
