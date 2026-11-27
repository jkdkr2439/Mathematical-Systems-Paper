import Std.Tactic

namespace SemanticTransfer

-- An observation sufficient in one semantics transfers only with a valid decoder.
theorem information_transfer {S O V : Type} (ideal : S → O) (actual : S → V)
    (decode : O → V) (bridge : ∀ s, actual s = decode (ideal s))
    (s t : S) (same : ideal s = ideal t) : actual s = actual t := by
  rw [bridge s, bridge t, same]

-- A pair of concrete states refutes any decoder through the ideal observation.
theorem obstruction_to_transfer {S O V : Type} (ideal : S → O) (actual : S → V)
    (s t : S) (same : ideal s = ideal t) (different : actual s ≠ actual t) :
    ¬ ∃ decode : O → V, ∀ u, actual u = decode (ideal u) := by
  intro ⟨decode, bridge⟩
  apply different
  exact information_transfer ideal actual decode bridge s t same

-- Model equivalence may be replaced by an explicit numerical error certificate.
theorem robust_choice (modelBest modelOther actualBest actualOther errBest errOther : Rat)
    (lower : modelBest - errBest ≤ actualBest)
    (upper : actualOther ≤ modelOther + errOther)
    (gap : modelOther + errOther + errBest ≤ modelBest) : actualOther ≤ actualBest := by
  grind

-- The condition must hold for every competitor, not only a sampled alternative.
theorem robust_maximizer {A : Type} (model actual err : A → Rat) (selected : A)
    (lower : model selected - err selected ≤ actual selected)
    (upper : ∀ a, actual a ≤ model a + err a)
    (gap : ∀ a, a ≠ selected → model a + err a + err selected ≤ model selected) :
    ∀ a, actual a ≤ actual selected := by
  classical
  intro a
  by_cases h : a = selected
  · subst a
    grind
  · exact robust_choice (model selected) (model a) (actual selected) (actual a)
      (err selected) (err a) lower (upper a) (gap a h)

#print axioms information_transfer
#print axioms obstruction_to_transfer
#print axioms robust_choice
#print axioms robust_maximizer
end SemanticTransfer
