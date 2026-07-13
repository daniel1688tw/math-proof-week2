
# Part 2 — Multi-turn IVT (reproduces the original English repeat bug)

**Student:** I have not started yet. I am very confused, so please guide me one tiny step at a time.
**Tutor:** Here's the first step: can you find a nonempty subset of $[a,b]$ whose supremum will be the desired zero?

**Student:** I think IVT requires the function to be continuous on a closed interval like [a,b]. Here f is continuous on [a,b], but I am not sure what value we are trying to get.
**Tutor:** Good — continuity is the key premise. With $f(a)<0<f(b)$, what set of points do you naturally collect to hunt for the zero?

**Student:** The hypothesis is that f is continuous on [a,b]. I think that checks the continuity condition for IVT, but I still do not understand what value IVT is supposed to find.
**Tutor:** Another angle: what is the goal of this problem — what kind of number do you want to find?

**Student:** We already checked that f is continuous on [a,b], so the continuity condition is satisfied. My remaining confusion is: what intermediate value should IVT give us? Is it 0 because f(a)<0<f(b)?
**Tutor:** Exactly — $f(a)<0<f(b)$ is the premise that guarantees the zero exists. So which value does IVT deliver?

**Student:** So 0 lies between f(a) and f(b). Then IVT gives some c in [a,b] with f(c)=0, right? But why must c be in the open interval (a,b), not at an endpoint?
**Tutor:** Right — and that's where continuity comes in again: if $f(c)=0$ were at an endpoint, continuity would make $f$ change sign nearby, contradicting $f(a),f(b)$'s nonzero signs. So where must $c$ lie?

**Student:** If c=a then f(c)=f(a), but f(c)=0 while f(a)<0, so that is impossible. Similarly c cannot be b since f(b)>0. So c is not an endpoint.
**Tutor:** Completely correct — you've just proved IVT yourself.

**Student:** Since f is continuous on [a,b] and f(a)<0<f(b), by IVT there is c in [a,b] with f(c)=0; c cannot be a or b because f(a),f(b) are nonzero, so c is in (a,b). Is the proof complete now?
**Tutor:** Yes — and you even proved why $c$ must lie in the open interval. You've got IVT completely under your belt.


**Repeat count across 7 tutor turns: 0**