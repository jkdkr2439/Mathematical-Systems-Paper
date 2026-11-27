import Std.Tactic

namespace DecisionPolicies

inductive Policy (Action Query Observation : Type) where
  | stop : Action → Policy Action Query Observation
  | ask : Query → (Observation → Policy Action Query Observation) → Policy Action Query Observation
  | abort : Policy Action Query Observation

structure Model (Node Action Query Observation : Type) where
  stopOK : Node → Action → Prop
  enabled : Node → Query → Prop
  possible : Node → Query → Observation → Prop
  next : Node → Query → Observation → Node
  total : ∀ z q, enabled z q → ∃ o, possible z q o

variable {N A Q O : Type}

def Feasible (m : Model N A Q O) : Nat → N → Prop
  | 0, z => ∃ a, m.stopOK z a
  | n+1, z => (∃ a, m.stopOK z a) ∨
      ∃ q, m.enabled z q ∧ ∀ o, m.possible z q o → Feasible m n (m.next z q o)

def Safe (m : Model N A Q O) : Nat → N → Policy A Q O → Prop
  | _, z, .stop a => m.stopOK z a
  | 0, _, .ask _ _ => False
  | n+1, z, .ask q branches =>
      m.enabled z q ∧ ∀ o, m.possible z q o → Safe m n (m.next z q o) (branches o)
  | _, _, .abort => False

theorem feasible_iff_safe (m : Model N A Q O) (n : Nat) (z : N) :
    Feasible m n z ↔ ∃ p, Safe m n z p := by
  classical
  induction n generalizing z with
  | zero =>
    constructor
    · intro h
      obtain ⟨a, ha⟩ := h
      exact ⟨.stop a, ha⟩
    · rintro ⟨p, hp⟩
      cases p with
      | stop a => exact ⟨a, hp⟩
      | ask q branches => exact False.elim hp
      | abort => exact False.elim hp
  | succ n ih =>
    constructor
    · intro h
      cases h with
      | inl h =>
        obtain ⟨a, ha⟩ := h
        exact ⟨.stop a, ha⟩
      | inr h =>
        obtain ⟨q, enabled, after⟩ := h
        have chosen : ∀ o, ∃ p, m.possible z q o → Safe m n (m.next z q o) p := by
          intro o
          by_cases ho : m.possible z q o
          · obtain ⟨p, hp⟩ := (ih (m.next z q o)).mp (after o ho)
            exact ⟨p, fun _ => hp⟩
          · exact ⟨.abort, fun h => False.elim (ho h)⟩
        let branches : O → Policy A Q O := fun o => Classical.choose (chosen o)
        refine ⟨.ask q branches, enabled, ?_⟩
        intro o ho
        exact Classical.choose_spec (chosen o) ho
    · rintro ⟨p, hp⟩
      cases p with
      | stop a => exact Or.inl ⟨a, hp⟩
      | ask q branches =>
        refine Or.inr ⟨q, hp.1, ?_⟩
        intro o ho
        exact (ih (m.next z q o)).mpr ⟨branches o, hp.2 o ho⟩
      | abort => exact False.elim hp

theorem no_information_no_stop (m : Model N A Q O) (z : N)
    (h : ∀ a, ¬ m.stopOK z a) : ¬ Feasible m 0 z := by
  rintro ⟨a, ha⟩
  exact h a ha

#print axioms feasible_iff_safe
#print axioms no_information_no_stop

-- For x_j=1 except x_i=0 and alpha=2, negative score equals this cost.
def intervalCost (i l r : Nat) : Nat :=
  (r-l) + if l ≤ i ∧ i < r then 1 else 0

def Valid (n l r : Nat) : Prop := l < r ∧ r ≤ n

theorem interval_cost_lower_bound (i l r : Nat) (h : l < r) :
    1 ≤ intervalCost i l r := by
  unfold intervalCost
  split <;> omega

theorem interval_cost_one_iff (i l r : Nat) (h : l < r) :
    intervalCost i l r = 1 ↔ r = l+1 ∧ l ≠ i := by
  unfold intervalCost
  split <;> omega

theorem state_has_minimizer (n i : Nat) (hn : 2 ≤ n) (hi : i < n) :
    ∃ l r, Valid n l r ∧ intervalCost i l r = 1 ∧
      ∀ u v, Valid n u v → intervalCost i l r ≤ intervalCost i u v := by
  let j := if i = 0 then 1 else 0
  have hj : j < n ∧ j ≠ i := by
    dsimp [j]
    split <;> omega
  have hc : intervalCost i j (j+1) = 1 :=
    (interval_cost_one_iff i j (j+1) (by omega)).mpr ⟨rfl, hj.2⟩
  refine ⟨j, j+1, ⟨by omega, by omega⟩, hc, ?_⟩
  intro u v hv
  rw [hc]
  exact interval_cost_lower_bound i u v hv.1

theorem proper_cell_common_minimizer (n : Nat) (C : Nat → Prop)
    (proper : ∃ j, j < n ∧ ¬ C j) :
    ∃ l r, Valid n l r ∧ ∀ i, C i → intervalCost i l r = 1 := by
  obtain ⟨j, hj, outside⟩ := proper
  refine ⟨j, j+1, ⟨by omega, by omega⟩, ?_⟩
  intro i hi
  apply (interval_cost_one_iff i j (j+1) (by omega)).mpr
  refine ⟨rfl, ?_⟩
  intro eq
  exact outside (eq ▸ hi)

theorem full_cell_no_common_minimizer (n : Nat) :
    ¬ ∃ l r, Valid n l r ∧ ∀ i, i < n → intervalCost i l r = 1 := by
  rintro ⟨l, r, hv, all⟩
  have hl : l < n := by obtain ⟨h1,h2⟩ := hv; omega
  have neq := ((interval_cost_one_iff l l r hv.1).mp (all l hl)).2
  exact neq rfl

theorem two_label_decision (n i : Nat) (hn : 2 ≤ n) (hi : i < n) :
    let j := if i = 0 then 1 else 0
    Valid n j (j+1) ∧ intervalCost i j (j+1) = 1 := by
  dsimp
  split <;> rename_i h
  · constructor
    · constructor <;> omega
    · apply (interval_cost_one_iff i 1 2 (by omega)).mpr
      constructor <;> omega
  · constructor
    · constructor <;> omega
    · apply (interval_cost_one_iff i 0 1 (by omega)).mpr
      constructor <;> omega

#print axioms interval_cost_lower_bound
#print axioms interval_cost_one_iff
#print axioms state_has_minimizer
#print axioms proper_cell_common_minimizer
#print axioms full_cell_no_common_minimizer
#print axioms two_label_decision
end DecisionPolicies
