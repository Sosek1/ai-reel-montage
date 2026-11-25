---
date: 2026-11-25
stage: "2 of 3 — documentation knowledge base (Context7)"
change_id: smooth-camera-path
slice: S-03
researcher: Claude (session run for Bartosz Sosin)
git_commit: 4fce46a
status: complete
next_stage: "3 of 3 — synthesis via /10x-research, separate session, Fable"
---

# Knowledge base: S-03 smooth-camera-path (research stage 2 of 3)

## What this document is

Stage 2 of the three-stage technique research that `CLAUDE.md` rule 6 prescribes. Stage 1
(`research/web-findings.md`) collected what the literature says and left a worklist of library
modules; this document answers, **per function**, the six questions the slice needs: signature and
parameters, weight handling, edge and missing-data behaviour, determinism, availability at the
pinned version, and cost at our scale.

**It does not choose a technique.** That is stage 3 (`/10x-research`) and `/10x-plan`. Nothing
here was run against `transfer-01a1f923/`, nothing was rendered, no production code was written.

### Sources and how they are labelled

| Label | Meaning |
| --- | --- |
| **[C7]** | Context7 MCP, with the library ID and the upstream file the snippet came from. |
| **[DOC]** | Official docstring of the function **as installed** (`scipy 1.18.1` in this repo's `.venv`), read with `uv run python -c "print(f.__doc__)"`. This is the same reference text the HTML manual renders, pinned to our version. |
| **[SRC]** | The installed implementation source, read to settle a behaviour the docstring leaves open. |
| **[FACT]** | A fact established by running the function on a 1 000-point synthetic random walk in the scratchpad — existence, acceptance of an argument, repeat-run hash, wall time. No project material involved. |
| **[INF]** | My inference from the above. Not documentation. |

Context7 library IDs used: `/scipy/scipy/v1.18.1`, `/scipy/scipy/v1.17.1`, `/cvxpy/cvxpy`,
`/websites/statsmodels_stable`, `/derb12/pybaselines`, `/rlabbe/filterpy`.

### Versions in play

`pyproject.toml` declares `scipy>=1.14`, `numpy>=2.0`; `uv.lock` pins **scipy 1.18.1** and
**numpy 2.5.5** [FACT, read from the files]. Every function below was confirmed importable with a
live signature at that pin.

### The one question this stage was opened to settle

**`scipy.signal.whittaker_henderson` is new in SciPy 1.18.0.** [C7
`/scipy/scipy/v1.18.1`, `doc/source/release/1.18.0-notes.rst`] — it is named under "Highlights of
this release" (*"`scipy.signal.whittaker_henderson` now provides access to Whittaker-Henderson
smoothing of a discrete signal"*) and again under *scipy.signal improvements*. The 1.17.1
documentation set has no trace of it [C7 `/scipy/scipy/v1.17.1`, queried for Whittaker-Henderson:
returns only smoothing-spline and `spline_filter` material]. **Consequence:** using it means
raising `pyproject.toml` from `scipy>=1.14` to `scipy>=1.18`. Open point 5 of stage 1 is closed.

---

## Part A — scipy functions already in the stack

### A1. `scipy.signal.whittaker_henderson` — penalised least squares (candidate 1)

**Signature** [FACT, `inspect.signature`]:
`whittaker_henderson(signal, *, lamb="reml", order=2, weights=None)`

**Parameters** [DOC]:

- `signal` — one-dimensional, **equidistant** data points, length at least `order + 1`.
- `lamb` — smoothing/penalty strength. `"reml"` (the default) **optimises the restricted maximum
  likelihood criterion to choose it from the data**; a non-negative number is used directly.
- `order` — order of the difference penalty, default `2`, at least `1`. Order 2 is the
  Hodrick–Prescott filter [DOC, and [C7] 1.18.0 notes say the same].
- `weights` — *case weights*, one per sample, `None` ≡ all ones.

**Units of the smoothing strength.** The objective is
`argmin_x Σ wᵢ(yᵢ − xᵢ)² + λ Σ (Δᵖ xᵢ)²` [DOC]. λ is therefore **not** in seconds or hertz: it
trades squared pixels of data fit against squared pixels of the p-th difference *per sample step*.
[INF] Its numeric value is tied to the sample rate — a path resampled from 16.67 Hz to 50 Hz would
need a different λ for the same visual result. Stage 3 should treat λ as a quantity to calibrate
against the material, not to port from a paper.

**Return value** [DOC]: a `_RichResult` (an `OptimizeResult`-like object) with `.x`, the smoothed
signal, and `.lamb`, the penalty actually used — the input number, or the REML-chosen value.

**Weights: YES, and zero weights are the documented mechanism.** [DOC] *"One of the nice
properties of WH is that it automatically performs inter- and extrapolation of data … Set
`weights = 0` for regions where you want to extra- or interpolate. The values of `signal` don't
matter if `weights = 0`."* This is exactly the treatment stage 1 derived from Eilers and Fessler
for a sample carrying no independent information.

**What it draws across a zero-weight region** [DOC]: *"WH interpolates a polynomial of
`degree = 2 * order - 1` and it extrapolates a polynomial of `degree = order - 1`. For
`order = 2`, this means cubic interpolation and linear extrapolation."* So at order 2 a no-ball
run becomes a cubic joining both sides with matching slope, and a run touching the end of a window
becomes a straight line.

**NaN handling** [FACT]:

- NaN in `signal` **at a position whose weight is 0** is accepted; the output is finite
  everywhere. The upstream docstring example does precisely this with NASA temperature data
  (`w[np.isnan(temperature)] = 0`) [DOC].
- NaN in `signal` with **no** zero weight raises
  `ValueError("Input array signal must be finite.")` [FACT; raised at `scipy/signal/_whittaker.py:225`].

[INF] For our data that is a clean fit: our 4.8% no-ball samples are NaN and would get weight 0;
our 21.3% predicted samples are finite and would get whatever weight stage 3 decides.

**Edges.** No windowing, no padding, no edge loss — every input position gets an output. [INF]
A 60-second window is solved as one system, so the ends are fitted as part of the whole rather
than mirrored or trimmed, unlike every convolution candidate.

**Determinism.** Two regimes, and they differ:

- **Fixed `lamb`:** the solve goes to LAPACK banded Cholesky (`pbsv`, with a tridiagonal `ptsv`
  fast path), obtained via `get_lapack_funcs(..., ilp64="preferred")` [SRC,
  `scipy/signal/_whittaker.py:46,55-58`]. [INF] That is a fixed-sequence banded factorisation, not
  a threaded BLAS-3 kernel, so repeat runs on one machine are byte-identical and thread count is
  not a factor. Confirmed by repeat-run hash [FACT].
- **`lamb="reml"` (the default):** the criterion is minimised with
  `minimize_scalar(criterion, bracket=[-10, 10])` [SRC, line 244] — Brent's method. Repeat runs on
  one build are byte-identical [FACT], but [INF] the chosen λ is a converged optimiser output, so
  it is the piece most exposed to a scipy upgrade, and λ varies with the data, meaning the two
  evaluation windows would be smoothed with **different** strengths. Observed on synthetic data:
  REML picked `lamb ≈ 2.35` on a pure random walk [FACT] — very light smoothing, because a random
  walk is "all signal" to the criterion.

[INF] A further caution for our case, following stage 1's Q3: 21.3% of our samples are exact
straight-line interpolations, i.e. have *zero* noise. Any data-driven λ selector (REML here, GCV
for the splines) reads that as "the data are less noisy than they are" and is biased toward
under-smoothing. Stage 3 should compare REML against a hand-set λ.

**Cost at our scale** [FACT, n = 1 000]: fixed λ ≈ **0.1 ms**; `lamb="reml"` ≈ **2 ms**. Banded,
O(n). Not a constraint at any window length we care about.

**Availability:** scipy **≥ 1.18.0** only — see the version note above. **Newer than the current
`>=1.14` floor.**

---

### A2. `scipy.interpolate.make_smoothing_spline` — GCV cubic smoothing spline (candidate 2)

**Signature** [FACT]: `make_smoothing_spline(x, y, w=None, lam=None, *, axis=0)`

**Parameters** [C7 `/scipy/scipy/v1.18.1`,
`doc/source/tutorial/interpolate/smoothing_splines.rst`]: it minimises
`Σ (yⱼ − g(xⱼ))² + λ ∫ g''(x)² dx`, i.e. the penalty is an **integral of the squared second
derivative over the interval**, not a sum of differences. *"it accepts an optional `lam` keyword
argument to specify the penalty parameter λ. If omitted or set to `None`, λ is computed via the
GCV procedure."* It is a clean-room reimplementation of Woltring's `gcvspl` Fortran package [C7,
same file]. Returns a `BSpline`.

**Units of the smoothing strength.** [INF] Because the penalty is an integral in `x`, λ is tied to
the units of `x`. Passing seconds and passing sample indices give different λ scales for the same
curve — a real trap when the same number is carried between experiments.

**Weights: partially.** `w` is accepted, and the tutorial flags a convention difference that
matters: *"`make_smoothing_spline` squares the weights to be consistent with `gcvspl`, while
`make_splrep` does not — to be consistent with FITPACK"* [C7, same file]. **But zero weights are
rejected**: the implementation validates `if any(w <= 0): raise ValueError('Invalid vector of
weights')` [SRC, `scipy/interpolate/_bsplines.py:2601`], confirmed at runtime [FACT]. So
"down-weight a predicted sample" works; "exclude it with w = 0" does **not**.

[INF] Two workarounds, both sound for a spline and neither available to a convolution filter:
(a) **drop the rows** — the fit is over scattered `(x, y)`, so `x` need not be uniform, and the
spline simply has no data in the gap; verified to work and to evaluate inside the gap [FACT];
(b) pass a **tiny positive weight** (`1e-8`), which is accepted [FACT] but is the "extreme weight"
pattern Fessler warns against in stage 1's Q3.

**NaN handling.** None: NaN must be removed from `x`/`y` before the call. [INF] That is the same
dropping operation as (a), so for us the two problems collapse into one.

**Edges.** As a spline fit it covers the whole interval with no trimming; evaluation outside
`[x₀, xₙ]` extrapolates and [C7, the `splrep` tutorial] warns extrapolated values *"vary wildly
with s"* for the FITPACK route. [INF] We never need to evaluate outside the window.

**Evaluation at frame times — the distinguishing feature.** The result is a `BSpline` callable at
arbitrary `t`, with `.derivative()` available. [INF] This is what candidate 2 buys over candidate
1: the 16.67 Hz path and the 50 fps frame grid are one object, no second upsampling step, and
velocity/acceleration for the metrics come out analytically rather than from `np.diff`.

**Determinism** [FACT]: repeat runs byte-identical, with `lam` given and with GCV. [INF] GCV is
again a data-driven selector with the same under-smoothing bias described in A1, and the same
version-exposure.

**Cost** [FACT, n = 1 000]: GCV path ≈ **0.19 s** — about 100× `whittaker_henderson`'s REML path,
still irrelevant against a render.

**Availability:** scipy **≥ 1.10.0** [C7 `/scipy/scipy/v1.18.1`,
`doc/source/release/1.10.0-notes.rst`: *"A new function `scipy.interpolate.make_smoothing_spline`
has been added"*]. Comfortably inside the current `>=1.14` floor.

---

### A3. `scipy.interpolate.make_splrep` / `splrep` / `UnivariateSpline` — FITPACK smoothing

**Signatures** [FACT]:
`make_splrep(x, y, *, w=None, xb=None, xe=None, k=3, s=0, t=None, nest=None, bc_type=None)`;
`splrep(x, y, w=None, xb=None, xe=None, k=3, task=0, s=None, t=None, ...)`;
`UnivariateSpline(x, y, w=None, bbox=[None, None], k=3, s=None, ext=0, ...)`.

**Smoothing strength is `s`, not λ** — a bound on the weighted sum of squared residuals, so `s=0`
interpolates and larger `s` smooths [C7 `/scipy/scipy/v1.17.1`, smoothing-splines tutorial:
*"Use s=0 for interpolation and s>0 for smoothing"*]. [INF] This is a different kind of knob from
λ: it is expressed in residual units, which makes it easier to set from a known noise level and
harder to reason about as "how stiff is the camera".

**Weights: YES, including zero.** `make_splrep` accepts `w = 0` entries [FACT] — it does not run
the `w <= 0` validation `make_smoothing_spline` does. Convention: **unsquared** weights, unlike
`make_smoothing_spline` [C7, tutorial note quoted in A2]. `splrep`/`UnivariateSpline` are the
legacy FITPACK interface to the same algorithm.

**NaN:** not handled; `UnivariateSpline` even defaults `check_finite=False` [FACT, signature],
which [INF] means NaN would propagate silently rather than raise — worth a guard if this route is
taken.

**Availability:** `make_splrep` is the modern spelling; `splrep`/`UnivariateSpline` are ancient.
All present at 1.18.1 [FACT]. [INF] Treat `make_splrep` as the one to use and the other two as
legacy.

---

### A4. `scipy.signal.savgol_filter` / `savgol_coeffs` — Savitzky–Golay (candidate 4)

**Signatures** [FACT]:
`savgol_filter(x, window_length, polyorder, deriv=0, delta=1.0, axis=-1, mode="interp", cval=0.0)`;
`savgol_coeffs(window_length, polyorder, deriv=0, delta=1.0, pos=None, use="conv", *, xp=None, device=None)`.

**Smoothing strength** is the pair `(window_length, polyorder)` — a window in **samples**, which
at 16.67 Hz converts directly to seconds. [INF] The sports precedent in stage 1 (a 0.5 s window)
would be `window_length ≈ 9` on our tracking grid, or `25` at 50 fps.

**`deriv` and `delta`** give the smoothed derivative directly [FACT, signature], which [INF] is
the cheapest route to the velocity/acceleration metrics stage 1's open point 4 lists.

**Weights: NO.** There is no weight argument [FACT, signature]. This is the structural limitation
stage 1 predicted for the whole convolution family.

**Edges** [DOC]: `mode` is `'mirror' | 'constant' | 'nearest' | 'wrap' | 'interp'`. *"When the
'interp' mode is selected (the default), no extension is used. Instead, a degree `polyorder`
polynomial is fit to the last `window_length` values of the edges, and this polynomial is used to
evaluate the last `window_length // 2` output values."* The other four modes pad the signal; the
ndimage boundary table [C7 `/scipy/scipy/v1.18.1`, `doc/source/tutorial/ndimage.rst`] documents
exactly what each padding does, including the `mirror`/`reflect` whole- vs half-sample distinction.

**NaN handling: destructive.** A 100-sample NaN run spread to **124 NaN outputs** with
`window_length = 25` [FACT] — the gap grows by half a window on each side. [INF] So a no-ball run
must be filled *before* this filter, which is precisely the imputation step stage 1 named as the
statistical mistake.

**Determinism.** [INF] A fixed FIR convolution with coefficients derived from a small
least-squares solve; no iteration, no solver, no randomness. Byte-reproducible.

**Cost:** O(n · window). Negligible.

**Availability:** scipy **0.14.0** [C7 `/scipy/scipy/v1.18.1`,
`doc/source/release/0.14.0-notes.rst`]. Far below the floor.

---

### A5. `scipy.signal.butter` + `sosfiltfilt` / `filtfilt` — zero-phase low-pass (candidate 3)

**Signatures** [FACT]:
`butter(N, Wn, btype="low", analog=False, output="ba", fs=None)`;
`sosfiltfilt(sos, x, axis=-1, padtype="odd", padlen=None)`;
`filtfilt(b, a, x, axis=-1, padtype="odd", padlen=None, method="pad", irlen=None)`.

**Smoothing strength is a cut-off frequency** — `Wn` with `fs` given, so in hertz. [INF] This is
the most physically legible knob of all the candidates ("the camera does not move faster than
0.5 Hz"), and the only one that transfers unchanged between the 16.67 Hz and 50 fps grids.

**Use `output="sos"`.** [INF] At the low orders we would use, `ba` is fine, but `sos` is the
numerically safe default and `sosfiltfilt` is its forward–backward partner. `sosfiltfilt` arrived
in SciPy 0.18.0 [C7 `/scipy/scipy/v1.18.1`, `doc/source/release/0.18.0-notes.rst`].

**Weights: NO.** No weight argument on any of the three [FACT].

**Edges** [DOC, `filtfilt`]: `padlen` *"must be less than `x.shape[axis] - 1`"*, default
`3 * max(len(a), len(b))`; `padtype` selects odd/even/constant extension; `padlen=0` disables
padding. `method="gust"` uses Gustafsson's method instead, ignoring `padtype`/`padlen`. [INF] With
~1 000 samples in a 60 s window the default pad is tiny relative to the signal, so the edge
transient stage 1 worried about is a non-issue at our window length — but it would bite on a very
short window, which S-05 may produce.

**NaN:** not handled; [INF] a NaN poisons the whole forward–backward pass, worse than
Savitzky–Golay's local spread.

**Determinism.** [INF] Fixed-sequence IIR recursions applied twice; no solver. Reproducible.
`method="gust"` solves a small linear system per edge — still deterministic, but [INF] a second
moving part for no gain here.

**Availability:** all three far below the floor (`filtfilt` 0.10.0, `sosfiltfilt` 0.18.0 [C7]).

---

### A6. `scipy.ndimage.gaussian_filter1d` / `uniform_filter1d` — kernel smoothing (candidate 5)

**Signatures** [FACT]:
`gaussian_filter1d(input, sigma, axis=-1, order=0, output=None, mode="reflect", cval=0.0, truncate=4.0, *, radius=None)`;
`uniform_filter1d(input, size, axis=-1, output=None, mode="reflect", cval=0.0, origin=0)`.

**Smoothing strength:** `sigma` in **samples**; the kernel is cut at `truncate = 4.0` standard
deviations unless `radius` overrides it [FACT, signature]. `order` gives Gaussian derivatives.

**Weights: NO** [FACT].

**Edges:** `mode` defaults to `"reflect"`. The ndimage tutorial gives the full table with worked
examples [C7 `/scipy/scipy/v1.18.1`, `doc/source/tutorial/ndimage.rst`]:
`nearest [1 2 3]→[1 1 2 3 3]`, `wrap →[3 1 2 3 1]`, `reflect →[1 1 2 3 3]`,
`mirror →[2 1 2 3 2]`, `constant →[0 1 2 3 0]`, plus the `grid-*` synonyms. [INF] For a camera
path `nearest` (hold the end value) is the one that does not invent motion at the window edge;
`reflect` mirrors the recent pan back on itself.

**NaN handling: destructive**, worse than Savitzky–Golay — a 100-sample NaN run became **140** NaN
outputs at `sigma = 5` [FACT], because the truncated kernel reaches `4σ`.

**Determinism.** [INF] Separable fixed-kernel correlation; reproducible.

**Availability:** ancient, well below the floor.

---

### A7. `scipy.optimize.linprog` — L1 formulations (candidates 7, 8)

**Signature** [FACT]:
`linprog(c, A_ub=None, b_ub=None, A_eq=None, b_eq=None, bounds=(0, None), method="highs", callback=None, options=None, x0=None, integrality=None)`.

**Methods** [C7 `/scipy/scipy/v1.18.1`, `doc/source/release/1.6.0-notes.rst`]: `"highs-ds"` is a
dual revised simplex, `"highs-ipm"` an interior-point method with crossover, `"highs"` chooses
between them; the notes say these *"are typically much faster and often exceed the accuracy of
other `linprog` methods"* and recommend naming one explicitly. `"highs"` is already the default at
1.18.1 [FACT, signature].

**Weights:** not a parameter, but [INF] per-sample weights enter an L1 problem as per-term
coefficients in `c`, and excluding a sample is dropping its residual term entirely. So the L1
route expresses weights as naturally as the L2 one — just by construction rather than by keyword.

**NaN:** [INF] no concept of it; a dropped sample is a dropped constraint.

**Edges:** [INF] none — like the penalised-least-squares routes it is a whole-window problem.
Ball-in-crop and `0 ≤ x ≤ 1312` can be hard constraints via `bounds` and `A_ub`, which is the
property candidates 8 and 9 exist for (and the one that would retire the post-hoc `check_follow`
overshoot risk carried from the S-02 review).

**Determinism** [FACT]: an ℓ1-trend-filter LP at our scale — 2 998 variables, 3 996 inequality
rows, built with `scipy.sparse` — solved to `status 0` and repeat runs were **byte-identical**.
[INF] That settles run-to-run reproducibility on one build. It does **not** settle reproducibility
across scipy/HiGHS versions: a simplex pivot order or an IPM tolerance change would move the
solution in the last bits, and a degenerate LP can have several optimal vertices. If this route is
chosen, pinning `scipy==` exactly (not `>=`) is the honest way to hold the byte-identical NFR,
and `method="highs-ds"` should be named rather than left to `"highs"` to pick.

**Cost** [FACT]: **0.07 s** for the problem above. A 60 s window is nowhere near a limit.

**Availability:** HiGHS methods since scipy 1.6.0 [C7]; below the floor.

---

### A8. `scipy.optimize.lsq_linear` — L2 path with hard bounds (candidate 9)

**Signature** [FACT]:
`lsq_linear(A, b, bounds=(-inf, inf), method="trf", tol=1e-10, lsq_solver=None, lsmr_tol=None, max_iter=None, verbose=0, *, lsmr_maxiter=None)`.

**Methods** [C7 `/scipy/scipy/v1.18.1`, `doc/source/release/0.17.0-notes.rst`]: a trust-region
method (`trf`) and Bounded-Variable Least-Squares (`bvls`); the trust-region methods *"also handle
sparse Jacobians"*. `Bounds` and `LinearConstraint` objects for the `minimize` route are
documented in the optimize tutorial [C7, `doc/source/tutorial/optimize.rst`].

**Weights:** [INF] no keyword, but the problem is stated as `min ||Ax − b||²` with bounds, so
per-sample weights are rows of `A` scaled by `√wᵢ`, and weight 0 is simply omitting the row. Same
expressive power as `whittaker_henderson`'s `weights`, at the cost of assembling the matrix.
The smoothing penalty becomes extra rows `√λ · D₂` stacked under the identity.

**Edges / NaN:** [INF] whole-window problem, no padding; NaN would have to be dropped as rows.

**Determinism** [FACT]: the stacked system above (1 998 rows × 1 000 columns, sparse) solved in
**0.04 s** with `nit = 0` — the unconstrained solution already satisfied the bounds — and repeat
runs were byte-identical. [INF] `nit = 0` means that run never exercised the iterative part; a
case where the touchline bound actually binds would iterate, and its reproducibility across
versions carries the same caveat as A7. `tol=1e-10` and `max_iter` are the knobs that would move
the answer.

**Availability:** scipy 0.17.0 [C7]; below the floor.

---

### A9. `scipy.interpolate.PchipInterpolator` / `CubicSpline` / `make_interp_spline` — upsampling 16.67 Hz → 50 fps

**Signatures** [FACT]:
`PchipInterpolator(x, y, axis=0, extrapolate=None)`;
`CubicSpline(x, y, axis=0, bc_type="not-a-knot", extrapolate=None)`;
`make_interp_spline(x, y, k=3, t=None, bc_type=None, axis=0, check_finite=True)`.

**The relevant documented property** [C7 `/scipy/scipy/v1.18.1`,
`doc/source/tutorial/interpolate/1D.rst`]: *"Cubic splines are by construction twice continuously
differentiable. This may lead to the spline function oscillating and 'overshooting' in between the
data points. In these situations, an alternative is to use the so-called monotone cubic
interpolants: these are constructed to be only once continuously differentiable, and attempt to
preserve the local shape implied by the data."* `PchipInterpolator` and `Akima1DInterpolator` are
the two offered.

[INF] For a camera path this is a real trade, not a detail. `CubicSpline` is C², which is what
"no visible kink in the motion" means, but it can overshoot past a sample — and an overshoot at
the touchline is exactly the right-edge violation the S-02 review (F4) warns about.
`PchipInterpolator` cannot overshoot but is only C¹, so its acceleration is discontinuous at every
sample — 16.67 times a second. Neither is obviously right; this is a stage-3 question.

**Weights:** none — these interpolate, they do not fit [FACT]. [INF] They are the *second* step
after a smoother that produced values at sample times (candidates 1, 3, 4, 5, 7–9); candidate 2
and the RTS smoother skip this step entirely by producing a function.

**Extrapolation:** `extrapolate` is a constructor argument on `PchipInterpolator`, and the
tutorial notes it has no `bc_type`, so `"periodic"` extrapolation *"wraps values without
guaranteeing derivative continuity"* [C7, same file]. [INF] Irrelevant for us.

**Determinism:** [INF] closed-form tridiagonal constructions; reproducible.

**Availability:** all ancient; `method="pchip"` on the grid interpolators came in 1.10.0 [C7].

---

### A10. `scipy.linalg.solveh_banded` / `solve_banded` / `cholesky_banded` — hand-written Whittaker

**Signatures** [FACT]:
`solveh_banded(ab, b, overwrite_ab=False, overwrite_b=False, lower=False, check_finite=True)`;
`solve_banded(l_and_u, ab, b, ...)`; `cholesky_banded(ab, overwrite_ab=False, lower=False, check_finite=True)`.

These wrap the LAPACK `*pbsv` / `*pbtrf` family — banded Cholesky factorisation and solve for a
symmetric positive-definite band matrix [C7 `/scipy/scipy/v1.18.1`,
`scipy/linalg/cython_lapack_signatures.txt`, entries `cpbtrf`, `cpbsvx`, `cpbrfs`, with `uplo`,
`kd` (number of sub/super-diagonals) and the `ab` band storage]. `scipy.sparse` + `spsolve` is the
alternative assembly route.

**Why this matters here** [INF]: this is the escape hatch. `whittaker_henderson` is 1.18-only, and
it fixes the penalty to plain `Δᵖ`. A hand-written `(W + λ DᵀD) x = W y` solved with
`solveh_banded` is perhaps fifteen lines of `core/` code, needs no version bump, keeps zero
weights and the gap-bridging property (they are properties of the objective, not of the wrapper),
and allows a mixed or position-dependent penalty if stage 3 wants one. What it does **not** give
is the REML λ selector. Note the 0.8.0-era return-value change [C7, `0.8.0-notes.rst`] is long
settled: `solveh_banded` returns just the solution.

[INF] `statsmodels.tsa.filters.hp_filter.hpfilter` is literally this, with `spsolve` — see C2.

---

## Part B — numpy helpers

No Context7 lookup was needed to establish behaviour that is not in question; recorded for
completeness because stage 1 listed them. `np.interp` (linear, the thing S-02 does today and that
S-03 replaces), `np.gradient`, `np.diff`, `np.clip`, `np.fft.rfft`, and
`np.lib.stride_tricks.sliding_window_view` are the pieces the metrics of stage 1's open point 4
would be built from. Pinned at **numpy 2.5.5** [FACT].

[INF] The one determinism caveat that applies to numpy generally and therefore to every candidate
above: pairwise summation in `np.sum`/`np.mean` is deterministic for a given array layout and
numpy build but is not associative, so a metric computed over a reordered or differently-strided
array can differ in the last bits. That affects *assertions*, not the path. `core/` must avoid
unseeded randomness and dict/set iteration order anyway, per `CLAUDE.md`.

---

## Part C — the four libraries outside the stack

The question for each is only: **does it earn a dependency?** The scope guard in `CLAUDE.md`
forbids a web framework, database, auth, GPU dependency or paid API. None of these four trips that
clause directly, so the test is the stricter one: does it do something scipy cannot, and is its
output deterministic?

### C1. `cvxpy` (+ OSQP / Clarabel / SCS / CVXOPT) — **do not add**

**What it would give:** candidates 7–9 written the way the papers write them —
`cp.Minimize(0.5*cp.sum_squares(y - x) + vlambda*cp.norm(D@x, 1))` with constraints as a list
[C7 `/cvxpy/cvxpy`, `doc/source/examples/applications/l1_trend_filter.rst`].

**The decisive evidence is in cvxpy's own ℓ1-trend-filtering example** [C7, same file]: the code
comment reads *"ECOS and SCS solvers fail to converge before the iteration limit. Use CVXOPT
instead"*, and the page ends with *"CVXPY is not optimized for the ℓ1 trend filtering problem. For
large problems, use l1_tf"* — i.e. the upstream project points away from itself for exactly our
problem.

**Dependencies and determinism:** which solvers exist is an installation property, not an API one
— `installed_solvers()` output in the docs lists eighteen backends including commercial ones [C7,
`doc/source/tutorial/solvers/index.rst`], so the solver that actually runs depends on what is
installed in the environment. [INF] That is the opposite of what a byte-identical-output NFR
needs: the result would depend on a solver choice that the lock file only partly determines, each
with its own iteration limits and tolerances, each compiled.

**Verdict: no.** `scipy.optimize.linprog(method="highs-ds")` solves the same LP in 0.07 s at our
size with one less compiled dependency and a solver the lock file fully pins [FACT, A7]. The only
thing cvxpy buys is readability of the problem statement, and that is not worth a solver stack.

### C2. `statsmodels` — **do not add**

**What it would give:** `tsa.filters.hp_filter.hpfilter(x, lamb=1600)` and the `tsa.statespace`
Kalman filter/smoother with missing-data support.

**`hpfilter` is strictly weaker than what we already have.** Its source is in the docs [C7
`/websites/statsmodels_stable`, `_modules/statsmodels/tsa/filters/hp_filter.html`]: it builds the
second-difference matrix `K` and returns `spsolve((eye + lamb*K.T.dot(K)).tocsc(), x)`. That is
`whittaker_henderson(order=2)` with all weights equal to one — **no `weights` argument, no missing
handling, no λ selection** (the default 1600 is a quarterly-macro convention). Ten lines of scipy
reproduce it exactly.

**The state-space side is genuinely capable but heavy.** Missing observations are handled properly
— the filter *"will produce forecasts, but forecast errors and the forecast error covariance
matrix will be zeros"* for completely missing observations, flagged as NaN, with
`missing_forecasts` keeping the recoverable values, and the smoother reorders around missing
entries [C7, `_modules/statsmodels/tsa/statespace/kalman_filter.html` and `kalman_smoother.html`].

**Verdict: no.** statsmodels pulls in pandas and patsy for two functions, one of which scipy
already subsumes and the other of which is stage 1's candidate 6 — about forty lines of numpy, per
stage 1's own assessment. [INF] A heavy transitive dependency in a pure-`core/` module that must
not touch IO is the wrong trade.

### C3. `filterpy` / `pykalman` — **do not add**

**What it would give:** `KalmanFilter.batch_filter(zs, Fs=None, Qs=None, Hs=None, Rs=None, ...)`
followed by `rts_smoother(Xs, Ps, Fs=None, Qs=None)` [C7 `/rlabbe/filterpy`,
`docs/kalman/KalmanFilter.rst`]. Two properties match our problem exactly:

- **Missing measurements:** *"Missing measurements must be represented by None"* in `zs` [C7,
  same file] — the "skip the update step" treatment stage 1 found in Särkkä.
- **Per-sample confidence:** `Rs` is *"optional list of values to use for the measurement error
  covariance R … This allows you to have varying R per epoch"* [C7,
  `docs/kalman/UnscentedKalmanFilter.rst`, same convention in `KalmanFilter`]. That is the
  inverse-variance weighting of stage 1's Q3, per sample.

**Against it:** the API is a Python loop over epochs with a list of `None`s, which [INF] sits
badly against our pure-`core/` contract of "arrays in, arrays out" and against mypy strict (no
stubs; it would need the same boundary-wrapping treatment as scipy, for a library with far less
scrutiny than scipy). filterpy is a teaching companion to a book, lightly maintained; pykalman
more so.

**Verdict: no.** Stage 1 already judged candidate 6 to be ~40 lines of numpy, and the two features
that would justify the dependency (`None` measurements, per-step `R`) are two `if` statements in a
hand-written RTS recursion. Determinism is then ours rather than a third party's. If the RTS route
is chosen in stage 3, write it.

### C4. `pybaselines` / `pentapy` — **do not add; read `pybaselines` as a reference**

**What it would give:** Whittaker smoothing with user weights and a `lam` parameter, over a family
of banded solvers, and the 2-D generalisation [C7 `/derb12/pybaselines`,
`docs/algorithms_2d/whittaker_2d.rst`, which states the weighted penalised objective and the
resulting linear system `(W_diag + λ DᵀD) v = w y` — the same equation as A1 and A10].

**On performance** [C7, `CHANGELOG.rst` v0.4.1]: it *"switched to using banded solvers for all
Whittaker-smoothing-based algorithms"* and added **pentapy** as an **optional** dependency whose
solver is *"faster than SciPy's `solve_banded` and `solveh_banded` functions, if pentapy is
installed and the system is pentadiagonal (`diff_order` is 2)"* — "~80-95% less time".

**Why that does not matter to us** [INF]: that speed-up is over a baseline that is already **0.1 ms**
at our size [FACT, A1]. Saving 90% of a tenth of a millisecond, a few hundred times per reel, is
nothing. pybaselines is also aimed at *baseline correction* of spectra — its headline algorithms
are iteratively reweighted (asymmetric least squares and relatives), which is a different problem
from ours.

**Verdict: no dependency, but worth reading.** Its 1-D Whittaker documentation is the clearest
published statement of the weighted banded formulation, and it is the right thing to consult if
stage 3 picks the hand-written route of A10.

---

## Summary table

Weights: **✓** = per-sample weights accepted; **✓ (w>0)** = weights accepted but zero rejected;
**✓ (by construction)** = no keyword, but the formulation carries weights as rows/terms;
**✗** = structurally impossible.

| Candidate (stage-1 #) | Function | Weights | Zero weight / exclusion | NaN gaps | Deterministic | scipy since | One-line assessment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `signal.whittaker_henderson` | **✓** `weights` | **✓ documented** — cubic across the gap at `order=2` | **✓** NaN allowed where `w=0`; raises otherwise | ✓ with fixed `lamb` (LAPACK banded Cholesky); REML adds a Brent minimisation | **1.18.0 — above the `>=1.14` floor** | Answers Q3 and the gaps in one call, fastest of all; costs a version bump and gives λ in per-sample units |
| 2 | `interpolate.make_smoothing_spline` | **✓ (w>0)**, *squared* | ✗ by weight — must drop the rows instead | ✗ — drop first | ✓; GCV is data-driven | 1.10.0 | Only candidate that is a *function*: evaluate at 50 fps and differentiate analytically, no upsampling step |
| 2b | `interpolate.make_splrep` | **✓**, *unsquared* | **✓** `w=0` accepted | ✗ | ✓ | long before 1.14 | FITPACK twin of #2 with `s` instead of λ and working zero weights |
| 3 | `signal.butter` + `sosfiltfilt` | **✗** | ✗ | ✗ poisons the pass | ✓ | 0.18.0 | Cut-off in Hz is the most legible knob and sample-rate independent; blind to confidence and to gaps |
| 4 | `signal.savgol_filter` | **✗** | ✗ | ✗ gap grows by ±½ window | ✓ | 0.14.0 | Window in samples, derivatives for free, `mode="interp"` needs no padding; no weights |
| 5 | `ndimage.gaussian_filter1d` | **✗** | ✗ | ✗ gap grows by ±4σ | ✓ | ancient | Five documented edge modes, trivially reproducible; the widest NaN spread of the three convolution filters |
| 6 | (hand-written RTS, see C3) | **✓** per-step `R` | **✓** skip the update | **✓** natural | ✓ | n/a — numpy | Expresses confidence and gaps most directly, yields velocity; must be written and has two noise parameters |
| 7, 8 | `optimize.linprog(method="highs-ds")` | **✓ (by construction)** | **✓** drop the term | **✓** drop the term | ✓ run-to-run [FACT]; across versions unproven | 1.6.0 | L1 paths and hard ball-in-crop constraints at 0.07 s for 3 000 variables; a solver in the determinism path |
| 9 | `optimize.lsq_linear` | **✓ (by construction)**, `√wᵢ` rows | **✓** omit the row | **✓** omit the row | ✓ run-to-run [FACT]; iterative when a bound binds | 0.17.0 | L2 smoothness with the touchline as a hard bound rather than a post-hoc check |
| — | `interpolate.PchipInterpolator` | ✗ | — | ✗ | ✓ | ancient | Upsampler that cannot overshoot the touchline, at the price of C¹ only |
| — | `interpolate.CubicSpline` | ✗ | — | ✗ | ✓ | ancient | C² upsampler, documented to overshoot between points |
| — | `linalg.solveh_banded` | **✓ (by construction)** | **✓** | **✓** | ✓ | ancient | The escape hatch: #1's objective hand-rolled, no version bump, custom penalties possible, no REML |
| out | `cvxpy` | ✓ | ✓ | ✓ | ✗ in practice — depends on which solver is installed | — | **No.** Its own docs say ECOS/SCS fail on ℓ1 trend filtering and point elsewhere |
| out | `statsmodels` | ✗ (`hpfilter`) / ✓ (statespace) | ✗ / ✓ | ✗ / ✓ | ✓ | — | **No.** `hpfilter` is `whittaker_henderson` with all weights 1; statespace drags pandas in for candidate 6 |
| out | `filterpy` / `pykalman` | **✓** `Rs` per epoch | **✓** `None` in `zs` | ✓ | ✓ | — | **No.** Right semantics, but it is ~40 lines of numpy and the library is unstubbed and lightly maintained |
| out | `pybaselines` / `pentapy` | ✓ | ✓ | ✓ | ✓ | — | **No dependency** — its speed-up is over a 0.1 ms baseline — but read its Whittaker docs if A10 is chosen |

---

## What the documentation does not settle — for stage 3 and the plan

Stage 1's five open points, updated, plus what reading the docs added.

1. **CLOSED — `whittaker_henderson` arrived in scipy 1.18.0** [C7, release notes]. Choosing it
   means `pyproject.toml` goes from `scipy>=1.14` to `scipy>=1.18`. `uv.lock` already pins 1.18.1,
   so nothing breaks today; it is a declaration to make honestly, not a migration.
2. **NARROWED — Open Roadmap Question 1.** The documentation now says plainly that
   `whittaker_henderson` and `make_splrep` *can* carry weight 0, `make_smoothing_spline` cannot,
   and the three convolution filters cannot carry weights at all. **What must still be measured:**
   whether weight 1 / reduced / 0 on the 21.3% predicted samples produces a visibly different path
   on the two evaluation windows. Documentation cannot answer that.
3. **NEW — is a data-driven λ safe here?** REML (`whittaker_henderson`) and GCV
   (`make_smoothing_spline`) both estimate the smoothing strength from the data's own noise. Our
   predicted samples have *exactly zero* noise, which biases both toward under-smoothing, and on a
   synthetic random walk REML chose a very weak λ ≈ 2.35 [FACT]. **Measure:** REML/GCV λ against a
   hand-set λ on both windows, and whether the two windows get similar λ — if they do not, a
   per-window λ makes the reel's two clips move differently, which is a product question, not a
   numerical one.
4. **NEW — which grid does the smoother run on?** Candidates 1, 3, 4, 5, 7–9 produce values at the
   16.67 Hz sample times and need a second upsampling step to 50 fps; candidate 2 and the RTS
   smoother produce an object evaluable at frame times. **Measure/decide:** smooth-then-upsample
   versus upsample-then-smooth, and if the former, `PchipInterpolator` (no overshoot, C¹) versus
   `CubicSpline` (C², can overshoot past the touchline). Overshoot here is the F4 right-edge risk.
5. **NEW — λ is not portable.** `whittaker_henderson`'s λ is per-sample-step, a smoothing spline's
   λ is per unit of `x`, FITPACK's `s` is in residual units, and only `butter`'s cut-off is in Hz.
   **The plan should record which units its tuning constant is in**, or the number will be
   misread the first time the sample rate or window length changes (S-05 produces shorter windows).
6. **STILL OPEN — L2 or L1** (stage 1 point 2). Unchanged: only rendered clips of both on the
   evaluation windows can settle it.
7. **STILL OPEN — check or constrain** (stage 1 point 3), now with cost numbers attached: the
   constrained routes are affordable (`linprog` 0.07 s, `lsq_linear` 0.04 s at n = 1 000 [FACT]).
   What is **not** settled is whether a solver belongs in a byte-identical-output path at all.
   Run-to-run reproducibility was confirmed on this build [FACT]; reproducibility across a scipy
   upgrade was not, and cannot be from documentation. **Decide in the plan:** if a solver route is
   taken, pin scipy exactly and name `method="highs-ds"` rather than `"highs"`.
8. **STILL OPEN — which numbers become assertions** (stage 1 point 4). Added: `savgol_filter`'s
   `deriv`/`delta` and `gaussian_filter1d`'s `order`, and a `BSpline.derivative()` if candidate 2
   is chosen, are the cheapest sources of the velocity/acceleration series those metrics need.
   Thresholds still have to come from the raw S-02 path as a baseline to beat.
9. **NEW — edge mode on short windows.** At ~1 000 samples per 60 s window the `filtfilt` default
   pad (`3 * max(len(a), len(b))`) is negligible [DOC], so stage 1's edge-transient worry is a
   non-issue at this length. **It becomes real for S-05's shorter windows**, and the ndimage mode
   choice (`nearest` holds the end value; `reflect` mirrors the pan back) changes what the camera
   does in the last half-second of a clip. Worth a named test either way.
