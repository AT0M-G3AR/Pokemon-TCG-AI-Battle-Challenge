import sys
import os

# Ensure we're running from the project root
sys.path.insert(0, 'agent')

from kaggle_environments import make
import importlib.util

# Import agent the same way Kaggle does
spec = importlib.util.spec_from_file_location("main", "agent/main.py")
mod  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
agent_fn = mod.agent

step_count  = [0]
errors      = []
unhandled   = []

def debug_agent(obs_dict):
    step_count[0] += 1
    step = step_count[0]

    try:
        result = agent_fn(obs_dict)
        select = obs_dict.get('select')

        if select is None:
            # Deck selection
            if len(result) != 60:
                msg = f"Step {step}: DECK ERROR — returned {len(result)} cards, expected 60"
                errors.append(msg)
                print(f"❌ {msg}")
            else:
                print(f"✅ Step {step}: Deck selection — 60 cards returned")
            return result

        options   = select.get('option', [])
        min_count = select.get('minCount', 1)
        max_count = select.get('maxCount', 1)
        context   = select.get('context', '?')
        n_options = len(options)

        # Check for invalid returns
        if result is None or len(result) == 0:
            # If min_count is > 0, an empty return is invalid
            if min_count > 0:
                msg = f"Step {step}: EMPTY RETURN ctx={context} minCount={min_count}"
                errors.append(msg)
                print(f"❌ {msg}")
            else:
                if step <= 40 or step % 20 == 0:
                    print(f"✅ Step {step:>3}: ctx={context:>3} options={n_options:>3} → {result}")
        elif len(result) < min_count:
            msg = f"Step {step}: TOO FEW ctx={context} returned={len(result)} need={min_count}"
            errors.append(msg)
            print(f"❌ {msg}")
        elif max(result) >= n_options:
            msg = f"Step {step}: OUT OF BOUNDS ctx={context} idx={result} max={n_options-1}"
            errors.append(msg)
            print(f"❌ {msg}")
        else:
            # Valid — print first 40 steps and any step divisible by 20
            if step <= 40 or step % 20 == 0:
                print(f"✅ Step {step:>3}: ctx={context:>3} options={n_options:>3} → {result}")

        return result

    except Exception as e:
        import traceback
        msg = f"Step {step}: EXCEPTION — {e}"
        errors.append(msg)
        print(f"❌ {msg}")
        traceback.print_exc()
        return []

print("=" * 60)
print("  Local Simulation — Agent Debug Runner")
print("=" * 60)

env = make("cabt")
env.run([debug_agent, debug_agent])

print()
print("=" * 60)
print(f"  Game complete — {step_count[0]} total steps")
print("=" * 60)

if errors:
    print(f"\n❌ ERRORS FOUND ({len(errors)}) — DO NOT SUBMIT:")
    for e in errors:
        print(f"   {e}")
else:
    print("\n✅ NO ERRORS — Safe to submit to Kaggle")

# Save replay
with open("replay_debug.html", "w") as f:
    f.write(env.render(mode="html"))
print("\nReplay saved → serve with: python3 -m http.server 8080")
print("Then open: http://localhost:8080/replay_debug.html")
