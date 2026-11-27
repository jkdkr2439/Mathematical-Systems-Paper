import Std.Tactic

namespace InteractionInformation

def run {S E : Type} (f : E → S → S) : List E → S → S
  | [], s => s
  | e::es, s => run f es (f e s)

def work {E : Type} (c : E → Nat) : List E → Nat
  | [] => 0
  | e::es => c e + work c es

def Agree {S E O : Type} (f : E → S → S) (o : S → O)
    (c : E → Nat) (b : Nat) (s t : S) : Prop :=
  ∀ w, work c w ≤ b → o (run f w s) = o (run f w t)

theorem budget_monotone {S E O : Type} (f : E → S → S) (o : S → O)
    (c : E → Nat) (b big : Nat) (s t : S) (h : b ≤ big) :
    Agree f o c big s t → Agree f o c b s t := by
  intro a w hw
  exact a w (Nat.le_trans hw h)

theorem residual_budget {S E O : Type} (f : E → S → S) (o : S → O)
    (c : E → Nat) (b : Nat) (e : E) (s t : S) :
    Agree f o c (c e + b) s t → Agree f o c b (f e s) (f e t) := by
  intro a w hw
  exact a (e::w) (Nat.add_le_add_left hw (c e))

theorem encoding_requires_refinement {S E O Z : Type}
    (f : E → S → S) (o : S → O) (c : E → Nat) (b : Nat)
    (enc : S → Z) (dec : List E → Z → O)
    (correct : ∀ w s, work c w ≤ b → dec w (enc s) = o (run f w s))
    (s t : S) (same : enc s = enc t) : Agree f o c b s t := by
  intro w hw
  rw [← correct w s hw, ← correct w t hw, same]

theorem new_observation_cannot_be_recovered {S A B : Type}
    (old : S → A) (fresh : S → B) (s t : S)
    (same : old s = old t) (different : fresh s ≠ fresh t) :
    ¬ ∃ repair : A → B, ∀ x, repair (old x) = fresh x := by
  intro ⟨repair, correct⟩
  apply different
  rw [← correct s, ← correct t, same]

theorem coupled_projection {S T A B U V : Type}
    (p : S → A) (q : T → B) (outS : S → U) (outT : T → V)
    (smallOutS : A → U) (smallOutT : B → V)
    (stepS : S → V → S) (stepT : T → U → T)
    (smallS : A → V → A) (smallT : B → U → B)
    (portsS : ∀ s, smallOutS (p s) = outS s)
    (portsT : ∀ t, smallOutT (q t) = outT t)
    (commS : ∀ s v, p (stepS s v) = smallS (p s) v)
    (commT : ∀ t u, q (stepT t u) = smallT (q t) u)
    (s : S) (t : T) :
    (p (stepS s (outT t)), q (stepT t (outS s))) =
    (smallS (p s) (smallOutT (q t)), smallT (q t) (smallOutS (p s))) := by
  rw [commS, commT, portsS, portsT]

#print axioms budget_monotone
#print axioms residual_budget
#print axioms encoding_requires_refinement
#print axioms new_observation_cannot_be_recovered
#print axioms coupled_projection
end InteractionInformation
