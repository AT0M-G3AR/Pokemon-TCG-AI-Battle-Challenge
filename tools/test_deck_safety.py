import sys
import json
sys.path.insert(0, 'agent')
import policy
from cg.api import *

# Mock state
obs = type('obj', (object,), {
    'current': type('obj', (object,), {
        'yourIndex': 0,
        'players': [type('obj', (object,), {
            'deckCount': 4,
            'hand': [type('obj', (object,), {'id': policy.DUDUNSPARCE})],
            'active': [type('obj', (object,), {'id': policy.ALAKAZAM, 'energies': [policy.PSYCHIC_ENERGY]})],
            'bench': [type('obj', (object,), {'id': policy.DUDUNSPARCE})],
            'prize': [1,2,3]
        }), type('obj', (object,), {
            'deckCount': 10,
            'prize': [1,2,3],
            'active': [],
            'bench': []
        })]
    }),
    'select': type('obj', (object,), {
        'context': SelectContext.MAIN
    })
})

# Test Ability options
options = [
    type('obj', (object,), {
        'type': OptionType.ABILITY,
        'area': AreaType.BENCH,
        'index': 0
    })
]

scores = policy.handle_main(obs, options, 1, 1)
print(f"Deck count 4 Dudunsparce Ability score: {scores[0]}")
