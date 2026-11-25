---
date: 2026-11-25
stage: "1 of 3 — web research (Exa)"
change_id: smooth-camera-path
slice: S-03
researcher: Claude (session run for Bartosz Sosin)
git_commit: 268beb2
status: complete
next_stage: "2 of 3 — documentation knowledge base (Context7), separate session, Fable"
---

# Web findings: S-03 smooth-camera-path (research stage 1 of 3)

## What this document is

Stage 1 of the three-stage technique research that `CLAUDE.md` rule 6 prescribes for a slice that
asks "which technique". It collects what the web says about turning a jittery ball trajectory
into a virtual camera path that reads as deliberate operator work. It **does not choose a
technique, design an API, measure anything on `transfer-01a1f923/`, or read library
documentation**. It ends with a list of candidate techniques and a list of library modules for
stage 2 to look up.

**Method.** 14 Exa searches (`web_search_exa`). Findings were taken from the result extracts
(abstracts and quoted body passages); no source was read in full, and where an extract was
visibly garbled (formulas lost in PDF extraction) that is said at the finding. Nothing here was
verified by running code.

**Evidence labels used throughout.**

- **[E] Established** — peer-reviewed paper, survey, textbook, or official reference
  documentation.
- **[P] Practice** — what a shipped system or open-source project does (shows it is done, not
  that it is right).
- **[O] Opinion** — a single blog post, forum answer or hackathon write-up. Useful as a lead,
  not as proof.

**Constraint labels.** Findings that need something the product does not have are tagged
**[needs: learned model]**, **[needs: GPU]**, **[needs: extra solver]** (a dependency beyond
numpy/scipy). Everything untagged is deterministic array maths.

**Our case, for reference** (measured in S-02, not re-measured here): 1920x1080 source at 50 fps,
608-wide crop moved horizontally, x in 0..1312; tracking every third frame (~16.67 Hz); 73.9%
detected, 21.3% "predicted" (in fact straight-line interpolation between detections, runs up to
2.64 s), 4.8% missing in 45 runs of 2.82–25.74 s; largest sample-to-sample jump 595 px.
Processing is offline: the whole window's ball track is known before the path is computed.

---

## Q1. Families of filters used on camera-driving trajectories

The video-stabilisation literature is the closest mature body of work: it has the same problem
(a noisy 1-D-per-parameter path, a crop window that must stay inside the frame, a result judged
by eye) and it has surveys. Three families recur.

### 1.1 Signal-processing filters (low-pass, Gaussian, Savitzky–Golay)

- **[E]** The ACM Computing Surveys review of video stabilisation classifies path smoothing into
  filtering-based (signal-processing and prediction/Kalman) and optimisation-based approaches.
  Low-pass and Gaussian filters are the most common choice "probably due to the ease of
  implementation"; their documented weakness is a single global strength: "applying a smoothing
  filter with global parameters was not appropriate, since instabilities and intentional motion
  vary throughout the video". A low sigma leaves jitter, a high sigma "cut[s] off the peak".
  Adaptive variants set sigma per sample, inversely to local motion intensity (Souza & Pedrini).
  — Souza, Maia, Pedrini, *Survey on Digital Video Stabilization*, ACM CSUR 2022,
  <https://dl.acm.org/doi/full/10.1145/3494525>; adaptive Gaussian:
  <https://link.springer.com/article/10.1186/s13640-018-0277-7>
- **[E]** Guilluy, Oudre, Beghdadi's overview says the same: the Gaussian filter is "very
  common", it "suppresses the high-frequency motion that are the most detrimental to visual
  comfort", and the kernel width is the strength knob; second-order filters with an
  application-chosen cut-off are the other variant.
  — *Video stabilization: overview, challenges and perspectives*, Signal Processing: Image
  Communication 2020, <https://www.laurentoudre.fr/publis/GOB-SPIC-20.pdf>
- **[E]** An IPOL comparison of smoothing strategies concludes that for arbitrary camera motion
  "Gaussian smoothing is recommended", with robust L1 regularisation as the alternative when
  crop size matters.
  — Sánchez, *Comparison of Motion Smoothing Strategies for Video Stabilization using Parametric
  Models*, IPOL 2017, <https://www.ipol.im/pub/art/2017/209/article.pdf>
- **[E]** A Savitzky–Golay filter is an ordinary FIR filter designed by local polynomial
  least-squares. Its frequency response is maximally flat at DC, which "guarantees that the first
  r moments of the input signal are preserved", so peak height and width survive; "the price to
  be paid is mediocre stopband attenuation". It is the suggested choice when signal and noise
  spectra overlap; when they are separated, a filter designed for stop-band attenuation is
  better. (StackExchange answer, but by a recognised DSP contributor and consistent with the
  S-G literature; treat as [E]-leaning.)
  — <https://dsp.stackexchange.com/questions/52219/savitzky-golay-filter-vs-iir-or-fir-linear-filter>
- **[P]** Disney Research's sports camera work post-smooths predicted pan angles with "a
  first-order Savitzky-Golay filter of 33 frames (0.5s)" at 60 fps, on the grounds that "smooth
  motion is critical for aesthetic camera work".
  — Chen & Carr, *Mimicking Human Camera Operators*, WACV 2015,
  <https://la.disneyresearch.com/wp-content/uploads/Mimicking-Human-Camera-Operators-Paper.pdf>
- **[P]** An open-source vertical-streaming project does: MAD-based outlier rejection on the ball
  x track → gap fill with `np.interp` → `gaussian_filter1d` with sigma = 15 frames → clip to frame.
  — <https://github.com/MdIslamNeon/Disney-SD-Smart-Vertical-Streaming>
- **[O]** A blog post argues for a zero-phase Butterworth over Savitzky–Golay in scientific
  post-processing (cleaner stop band, explicit cut-off in Hz), while showing both place a pulse
  peak at the right time.
  — <https://mvernacc.github.io/portfolio/blog/filters_savgol_vs_butter/>
- **[E]** Eilers lists Savitzky–Golay's practical disadvantages against a penalised
  least-squares smoother: no continuous control of smoothness (window/order are integers),
  awkward boundaries, no native handling of missing values or weights.
  — Eilers, *A Perfect Smoother*, Analytical Chemistry 2003,
  <https://pubs.acs.org/doi/abs/10.1021/ac034173t>

### 1.2 Prediction filters (Kalman and variants)

- **[E]** In stabilisation, the Kalman filter is used "mainly due to its adaptation for online
  stabilization, since it only needs the previous state". With a constant-velocity model "the
  smoothing intensity depends on the assumed acceleration variance. Lower values generate
  smoother paths". The survey's summary table lists the adaptive-Kalman line as "can be used in
  scenarios that require online stabilization" with the disadvantage "lower results compared to
  offline methods".
  — ACM CSUR 2022, <https://dl.acm.org/doi/full/10.1145/3494525>
- **[E]** Disney/Caltech on post-hoc Kalman smoothing of camera plans: it "can mitigate [jitter]
  to some degree, it is not ideal due to overly stringent modeling assumptions (e.g., Gaussian
  noise)".
  — Chen, Le, Carr, Yue, Little, CVPR 2016,
  <https://openaccess.thecvf.com/content_cvpr_2016/papers/Chen_Learning_Online_Smooth_CVPR_2016_paper.pdf>
- **[E]** The offline counterpart of the Kalman filter is the **Rauch–Tung–Striebel (RTS)
  fixed-interval smoother**: a forward filter pass plus a backward pass, giving
  p(x_t | all observations) rather than p(x_t | past). Cost is O(n) for a small state. Särkkä's
  texts are the standard reference.
  — Särkkä & Svensson, *Bayesian Filtering and Smoothing* (2023),
  <https://users.aalto.fi/~ssarkka/pub/bfs_book_2023_online.pdf>;
  <https://users.aalto.fi/%7Essarkka/pub/gp-ts-kfrts.pdf>
- **[O]** A hackathon team building exactly our product (landscape sports clip → 9:16 following
  the ball) reports: "We started the camera controller with a Kalman filter … It added hundreds
  of pixels of visible lag. The camera was always a half second behind the ball on fast plays",
  and replaced it with speed and acceleration caps. Note this was a **causal** filter; it says
  nothing about an RTS smoother.
  — Supersonics, Devpost, <https://devpost.com/software/supersonics>

### 1.3 Whole-trajectory optimisation (the offline family)

This is what the literature uses when the full path is known in advance.

- **[E]** **L1-optimal camera paths** (Grundmann, Kwatra, Essa, CVPR 2011 — the algorithm behind
  YouTube's stabiliser). Minimise w1·|D P|₁ + w2·|D² P|₁ + w3·|D³ P|₁ by linear programming,
  subject to constraints. Motivation is cinematographic: a pleasant path is made of a static
  camera (DP = 0), constant-velocity pans (D²P = 0) and constant-acceleration ease in/out
  (D³P = 0). "L1 optimization has the property that the resulting solution is sparse … The
  computed path therefore has derivatives which are exactly zero for most segments", whereas "the
  L2 optimized camera path always has some small non-zero motion". Constraints: the crop window
  stays inside the frame (hard), proximity to the original intent, and salient points inside the
  window (soft, "to prevent tracking of salient points, which in general leads to non-smooth
  motion"). The survey notes "without proper constraints, the optimal path is constant".
  — <https://faculty.cc.gatech.edu/~irfan/p/2011-Grundmann-AVSWROCP.pdf>
  **[needs: extra solver]** in the paper (an LP solver); stage 2 should check whether
  `scipy.optimize.linprog` (HiGHS) covers it.
- **[E]** **Virtual PTZ by cropping a static wide shot** (Gandhi, Ronfard, Gleicher, CVMP 2014)
  — structurally our problem: a crop window (centre, size) per frame inside a fixed master shot.
  Objective = squared distance of the crop centre from the subject's inclusion region
  + λ1·L1(first difference) + λ2·L1(third difference) + penalties, **subject to hard linear
  constraints** that the crop lies inside the master frame and encloses the subject region.
  Stated behaviours: L1 on velocity alone "tend[s] to give piecewise constant segments combined
  with fast transitions" with "sudden start and stop" and a "staircase artifact"; adding L1 on
  jerk gives "smooth transitions between long piecewise constant segments"; "a more common L2
  norm tends to spread the movement over many frames, leading to continual drifting motions".
  Solved with an off-the-shelf convex toolbox (cvx).
  — <https://cvit.iiit.ac.in/images/ConferencePapers/2014/vineeth_multi_clip.pdf>
  **[needs: extra solver]** as published.
- **[E]** **L2 path optimisation** (Liu et al., *Bundled camera paths*, SIGGRAPH 2013): minimise
  a data term (stay near the original path) plus an L2 smoothness term over a neighbourhood;
  smoothing strength is adapted per frame to "discontinuities, cropping size and geometrical
  distortion". The survey notes it "neither uses cinematographic nor physical rules".
  — <https://dl.acm.org/doi/10.1145/2461912.2461995>
- **[E]** **Penalised least squares on differences** — the Whittaker smoother, known in
  econometrics as the **Hodrick–Prescott filter** at order 2. Minimise
  Σ wᵢ(yᵢ − zᵢ)² + λ Σ (Δᵈ z)². This is one sparse banded linear solve, "extremely fast, gives
  continuous control over smoothness, interpolates automatically", "adapts to boundaries
  automatically". With large λ the result tends to a constant (d = 1), a straight line (d = 2)
  or a parabola (d = 3). It is exactly the "penalty on acceleration" (d = 2) or "penalty on jerk"
  (d = 3) formulation, in closed form.
  — Eilers 2003, <https://pubs.acs.org/doi/abs/10.1021/ac034173t>
- **[E]** **ℓ1 trend filtering** (Kim, Koh, Boyd, Gorinevsky, SIAM Review 2009): the same
  objective with the L1 norm on second differences. It "produces trend estimates that are
  piecewise linear"; "the kinks … can be interpreted as abrupt changes or events in the
  underlying dynamics"; with specialised interior-point methods the cost "grows linearly with
  the number of data points". Known weakness: as a shrinkage estimator it is biased in level.
  — <https://epubs.siam.org/doi/10.1137/070690274>; bias:
  <http://www.csam.or.kr/journal/view.html?doi=10.29220%2FCSAM.2023.30.2.149>
  Higher-order L1 penalties (trend filtering of order r; total-variation denoising is r = 1):
  <https://arxiv.org/abs/1702.05113>. **[needs: extra solver]** unless stage 2 finds an
  LP/QP route in scipy.
- **[E]** **Smoothing splines**: minimise Σ wᵢ(yᵢ − f(xᵢ))² + λ ∫ f''(u)² du; the solution is a
  natural cubic spline, λ can be picked by generalised cross-validation. Fessler notes that with
  uniform weights "spline smoothing approximately corresponds to a Butterworth low-pass filter
  of order 2m" — i.e. the spline, Whittaker and zero-phase low-pass families are close relatives
  and differ mainly in how they take weights, gaps and boundaries.
  — <https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.make_smoothing_spline.html>;
  <https://web.eecs.umich.edu/~fessler/papers/files/jour/93/web/fessler-93-tru.pdf>
- **[E]** **Path fitting**: fit constant / linear / quadratic models (still shot / tracking shot
  / transition) over time windows; "these models do not hold for long video sequences", hence
  splines or windowed fits blended with a Gaussian.
  — Guilluy et al., <https://www.laurentoudre.fr/publis/GOB-SPIC-20.pdf>
- **[P]** **Google AutoFlip** buffers a whole scene, then picks one of three modes —
  *stationary*, *panning* (constant velocity), *tracking* — and forms the path by
  "Euclidean-norm optimization, in which we minimize the residuals between a smooth (low-degree
  polynomial) camera path and the bounding boxes". A `motion_stabilization_threshold_percent`
  decides hold vs track: if all subjects stay within that fraction of the frame, the camera does
  not move at all. An alternative causal "kinematic" solver exposes `max_velocity`,
  `update_rate`, `min_motion_to_reframe` (a dead zone). Scenes are capped at `max_scene_size`
  (600 frames) — a single low-degree polynomial cannot describe long play.
  — <https://research.google/blog/autoflip-an-open-source-framework-for-intelligent-video-reframing/>;
  <https://mediapipe.readthedocs.io/en/latest/solutions/autoflip.html>;
  parameters as seen in a config: <https://github.com/Danil0v3s/autoflip/blob/main/input/autoflip_graph.pbtxt>

### 1.4 Causal followers (spring–damper, exponential, rate limits)

These come from game cameras and real-time broadcast; they are here because the brief asks, and
because their *behaviours* (dead zone, look-ahead) are reusable even offline.

- **[O]** Exponential follow p ← T + (p − T)·e^(−Δt/τ) and critically damped springs (Unity
  `SmoothDamp`, typical smooth time 0.1–0.25 s; "above 0.5 s the camera lags so far behind that
  the player runs off screen"). Lag is inherent: the camera "doesn't teleport to its target — it
  catches up". Games compensate with **look-ahead** (offset the target along the direction of
  travel) and **dead zones / camera windows** (no camera motion while the target stays inside a
  box).
  — <https://gamedev-canon.alekseiprikhodko.com/m03-cameras.html>;
  <https://devforgeunity.com/unity-2d-camera-follow/>;
  Keren, *Scroll Back* (GDC talk write-up), <https://gamedesignskills.com/game-design/camera-design-2d-side-scroller-games/>
- **[E]** Real-time virtual soccer camera (Bagadus, Tromsø): a **Schmitt trigger** servo — an
  imaginary window inside the view; while the ball is inside, the camera is braked to rest with
  a stopping acceleration; once it leaves, the camera accelerates toward it up to a maximum
  velocity. Three parameters: acceleration, maximum velocity, stopping acceleration. Reported
  trade-off: higher acceleration reaches the ball faster "but … also introduces uneasiness in
  watching"; higher maximum velocity tracks fast balls but "creates an undesired effect of
  overshooting". Evaluated by user studies against an expert human operator.
  — Gaddam, Eg, Langseth, Griwodz, Halvorsen, *The Cameraman Operating My Virtual Camera Is
  Artificial*, ACM TOMM 2015, <http://home.simula.no/~paalh/publications/files/tomm2015-cameraman.pdf>
- **[P]** H2V4Sports (Tsinghua, real-time horizontal-to-vertical for basketball/diving): a
  "momentum-based" update, crop centre = α·previous centre + (1 − α)·object centre, with α made
  a function of the displacement relative to the crop width so that large moves are followed
  faster. (The formula was garbled in extraction; the form is as described in the surrounding
  text.) **[needs: GPU, learned model]** for its detector — only the smoothing rule is relevant.
  — <https://mn.cs.tsinghua.edu.cn/xinwang/PDF/papers/2023_H2V4Sports%20Real-Time%20Horizontal-to-Vertical%20Video%20Converter%20for%20Sports%20Lives%20via%20Fast%20Object%20Detection%20and%20Tracking.pdf>

---

## Q2. Avoiding lag

- **[E]** Lag is a property of *causal* filtering, and we are not causal. "A causal digital
  filter delays different frequency components by different amounts … Forward-backward filtering
  eliminates phase distortion entirely by filtering the signal twice: once forward in time, once
  backward. The result has the squared magnitude response of the original filter and exactly
  zero phase shift at all frequencies. The price: it requires the entire signal in advance."
  Consequences to know: the effective order doubles ("a 4th-order Butterworth filtered
  forward-backward has an 8th-order magnitude rolloff"), and there are start/end transients that
  padding mitigates but does not remove ("some edge corruption is inherent to the method").
  — <https://dsp-workshop.nl/basics/zero-phase.html>; MathWorks `filtfilt` reference (zero phase,
  squared magnitude, doubled order; padding patterns "linear"/"reflect", Gustafsson's method for
  initial states): <https://www.mathworks.com/help/signal/ref/filtfilt.html>
- **[E]** Symmetric FIR kernels (Gaussian, centred moving average, Savitzky–Golay applied
  centred) are zero-lag by construction when applied offline. So are the whole-trajectory
  optimisers of 1.3 and the RTS smoother of 1.2: each output sample depends on samples on both
  sides. "For offline analysis, forward-backward IIR is usually preferable: lower order, no
  delay, sharp cutoff."
  — same sources; <https://dsp.stackexchange.com/questions/52219/savitzky-golay-filter-vs-iir-or-fir-linear-filter>
- **[E]** Zero phase does **not** mean a fast change is preserved. Any linear smoother that is
  strong enough to remove jitter also rounds a sharp turn *symmetrically*: the camera starts
  moving **before** the pass (which reads as anticipation — good) and is still off the ball at
  the corner (peak attenuation — the risk). The survey's wording for a global Gaussian is that it
  "completely cuts off the peak". This is the smoothness-versus-fidelity trade-off, and three
  answers appear in the literature:
  1. **Adaptive strength** — less smoothing where local motion is intense (adaptive Gaussian,
     Souza & Pedrini; "weights … adapted to preserve motion-discontinuity", Guilluy et al.).
  2. **L1 instead of L2 penalties** — keeps kinks sharp and segments exactly straight or
     exactly still (Grundmann; Gandhi; Kim et al.). EViews' comparison on an economic series:
     HP shows "relatively smooth transition behavior" around a shock, the ℓ1 filter captures the
     "V-shaped" pattern and is "more robust to end-point sensitivity" ([O]/[P]:
     <https://blog.eviews.com/2016/11/l1-trend-filtering_4.html>).
  3. **Hard constraints instead of fidelity** — do not ask the path to be near the ball; require
     only that the ball stays inside the crop (inclusion constraint), and let the optimiser be as
     smooth as that allows (Grundmann's inclusion/saliency constraints; Gandhi's hard linear
     constraints). This turns "do not lose a fast change" from a tuning hope into a guarantee.
- **[E]** A human reference point for what "responsive" looks like: in the Disney/Caltech soccer
  data, "the human demonstrations … were almost entirely piece-wise linear. In other words, the
  human expert is almost always directing the camera in a straight line with very sharp course
  corrections", and the authors suggest "L1 regularization … that prefers zero acceleration" to
  capture it. That is a description of soccer camera work specifically, from 91 minutes of a
  semi-professional match.
  — Chen et al., CVPR 2016 (link above)
- **[O]** The Supersonics team's finding that velocity + acceleration caps were "simultaneously
  smoother and more responsive" than their Kalman filter, using "a handful of frames of
  lookahead". Their per-sport caps: basketball 70 px/frame and 8 px/frame², football (American)
  180 and 28 — at an unstated resolution and frame rate, so the numbers do not transfer.
  — <https://devpost.com/software/supersonics>
- **[E]** A documented failure of smooth following in soccer: "when the ball moves slowly during
  few times and then a player makes suddenly a big shot. It is difficult with a smooth motion to
  follow the ball when its speed changes suddenly. In this case, several frames are necessary to
  refocus" — from a causal system; it is the case a non-causal method should be tested on.
  — Lavigne et al., *Automatic Video Zooming for Sport Team Video Broadcasting on Smart Phones*,
  VISAPP 2010, <https://www.scitepress.org/PublishedPapers/2010/28301/28301.pdf>

---

## Q3. Weighting samples by confidence — and what to do with interpolated ones (Open Roadmap Question 1)

No source addresses our exact situation (a tracker that emits linear interpolation labelled
"predicted"). The general principles are well established and point the same way.

- **[E]** **Weights are inverse variances.** In penalised regression and smoothing splines the
  data term is Σ wᵢ(yᵢ − f(xᵢ))² and the statistically motivated weight is the Fisher
  information, wᵢ = 1/σᵢ². Fessler: "This weighting diminishes the influence of high variance
  measurements"; with non-uniform weights "the 'impulse response' of the smoothing spline will be
  spatially variant" — the smoother automatically leans on neighbours where a sample is
  unreliable. Note scipy's convention difference flagged in its own docs:
  `make_smoothing_spline` uses wᵢ unsquared, `splrep` uses squared weights.
  — <https://web.eecs.umich.edu/~fessler/papers/files/jour/93/web/fessler-93-tru.pdf>;
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.make_smoothing_spline.html>;
  IMSL: weights should be the inverse of the error standard deviation,
  <https://help.imsl.com/c/cnlmath/current/cub_spline_smooth.htm>
- **[E]** **A sample with no information gets weight zero, i.e. is discarded.** Fessler:
  "it is possible to have detector measurements with zero information … a more appropriate
  approach is simply to discard the measurements with zero information" rather than use an
  extreme weight. Eilers: "The missing elements of y are set to an arbitrary value, say 0, and a
  vector w of weights is introduced, with wᵢ = 0 for missing observations and wᵢ = 1 otherwise …
  At the positions where y is missing, z is automatically and smoothly interpolated." SciPy's
  `whittaker_henderson`: "Set `weights = 0` for regions where you want to extra- or interpolate.
  The values of `signal` don't matter if `weights = 0`."
  — Eilers 2003; <https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.whittaker_henderson.html>
- **[E]** **State-space view: missing means "skip the update".** "Missing data can be treated by
  simply skipping the update step of Kalman filter"; the smoother then bridges the gap using
  both sides, with uncertainty widest mid-gap. Per-sample confidence is the measurement variance
  R_k, which may differ at every step.
  — Särkkä, <https://users.aalto.fi/%7Essarkka/pub/gp-ts-kfrts.pdf>; Peng,
  <https://bookdown.org/rdpeng/timeseriesbook/missing-data.html>; Tsay ch. 11 notes,
  <https://qihongruan.github.io/tsay-time-series/en/chapters/ch11.html>
- **[E]/[O]** **Feeding interpolated values in as observations is the named mistake.** An
  imputed value "enters the fit with the same weight as a real observation, so standard errors …
  all sharpen as if data existed where it did not"; advice: "never impute before state-space
  modeling; pass the gaps through" ([O], course material:
  <https://www.ervads.com/courses/applied-time-series-3/sample>). Peer-reviewed support for the
  mechanism: linear interpolation "always leads to underestimation of the prediction
  uncertainty due to the averaging effect" (Lepot, Aubin, Clemens, *Water* 2017,
  <https://doi.org/10.3390/w9100796>), and "results are biased because the interpolation acts as
  a filter" (PTTI 1998, <http://time.kinali.ch/ptti/1998papers/Vol%2030_03.pdf>).
- **[E]** **What a smoother puts in place of dropped samples depends on its order.** With zero
  weights the Whittaker smoother of order d interpolates a polynomial of degree 2d − 1 (order 2
  → cubic) and extrapolates one of degree d − 1 (order 2 → straight line). A constant-velocity
  RTS smoother behaves equivalently. So "drop the predicted samples" replaces a straight chord
  with corners at both ends by a cubic that joins both sides with matching slope.
  — Eilers 2003; scipy `whittaker_henderson` docs (link above)
- **[P]** Sports systems in practice use detector confidence only as a gate (choose the
  highest-confidence detection, reject outliers by MAD on the x track) and then smooth all
  surviving and gap-filled samples uniformly (Disney-SD project; Chen & Carr "linearly
  interpolated the tracking data to 60fps" before use). Nobody in the sample weighted the
  smoother itself.

**What this means for the open question (a reading of the sources, not a decision).** The three
options the brief names map onto established practice as follows: *exclude* = zero weight /
skip update, the textbook treatment of a sample with no independent information; *weight lower*
= inverse-variance weighting, appropriate if the interpolated position is believed to be a
noisier but real estimate; *leave unchanged* = the documented mistake in a statistical sense,
though harmless to the eye if the chord is short. What the sources cannot say is whether the
difference is **visible** on our material: our predicted runs are short (≤ 2.64 s) and the
straight chord between two detections is already close to what a second-order smoother would
draw. What remains artificial is the pair of slope discontinuities at the ends of each run, and
the fact that 21.3% of samples have exactly zero noise while their neighbours do not, which
biases any data-driven choice of smoothing strength (GCV, REML) toward under-smoothing. Whether
that matters is an empirical question for stage 3 / the plan: compare paths with predicted
samples at weight 1, at reduced weight and at weight 0 on the two evaluation windows.

A practical consequence for the technique shortlist: **convolution-type filters
(Savitzky–Golay, Gaussian, Butterworth `filtfilt`) take no per-sample weights at all**. If the
answer to the open question is "treat predicted samples differently", the candidates shrink to
penalised least squares (Whittaker), smoothing splines, the RTS smoother and the
constrained optimisers.

---

## Q4. How sports virtual framing is built in practice

- **[E]** **Common architecture**: detect/track → pick one target point per frame → smooth →
  crop/render. Smoothing is a separate stage operating on a 1-D (pan) signal; tilt and zoom are
  frequently held fixed (Chen & Carr: "we focus on predicting an appropriate pan angle"; Chen et
  al. 2016: "tilt and zoom … do not vary significantly"). Our horizontal-only crop is the
  standard simplification, not a shortcut.
- **[E]** **The ball is the right signal for soccer.** Disney/Caltech's learned planner worked
  for basketball but "the results for soccer were much poorer … lack of ball tracking in the
  input signal x is a significant limitation in the soccer setting", because soccer players
  hold formation rather than follow the ball. **[needs: learned model]** for their method; the
  observation stands on its own.
  — CVPR 2016 (link above); press summary <https://phys.org/news/2016-06-human-camera-automated-sports.html>
- **[E]** **Velocity and acceleration limits are standard in real-time systems.** Bagadus:
  acceleration, maximum velocity, stopping acceleration (section 1.4). Lavigne et al. (soccer to
  a 360x640 phone screen): the crop centre moves by the mean ball displacement over the last
  n = 10 frames divided by a smoothing factor β = 15, with a hard per-frame cap
  ‖Cᵢ − Cᵢ₋₁‖ < Dₛ, at 25 fps; parameters "chosen after few visual tests". (Their formulas were
  partly garbled in extraction.)
- **[E]** **Abrupt changes of play** are handled in three ways across the sources: (a) accept a
  few frames of re-centring (Lavigne); (b) a window/dead zone so small ball motion moves nothing
  and large motion triggers a deliberate, rate-limited move (Bagadus Schmitt trigger; AutoFlip's
  stabilisation threshold and `min_motion_to_reframe`); (c) optimise the whole clip so the move
  starts early (Grundmann, Gandhi, AutoFlip's scene buffering). A fourth, coupling speed to zoom
  — "if the ball moves fast, the zoom has to be small because it is easier for the zooming frame
  to follow action" (Lavigne) — belongs to S-04.
- **[E]** **"Do not track the ball exactly" is a design principle, not a compromise.**
  Grundmann models saliency as a soft constraint precisely "to prevent tracking of salient
  points, which in general leads to non-smooth motion of the non-salient regions" — the
  background (pitch, stands) is what the viewer's eye reads camera motion from. Gandhi adds
  an "apparent motion" term: if the subject is static the window must not move, and the
  subject's on-screen direction of motion must match its real direction.
- **[O]** A practical bug class worth a test: Supersonics stored the *attempted* per-frame delta
  rather than the *achieved* one after clamping at the frame edge, "so clamped frames were
  silently accumulating momentum" and the crop stayed pinned to the edge for several frames
  after the ball turned. Relevant to our carried-over right-edge requirement (`check_follow`,
  x ≤ 1312): any stateful method must clamp inside the recursion, and any linear smoother can
  overshoot the bound and then be clipped, producing a flat spot with a corner.
- **[P]** A basketball vertical-crop project plans "the framing for the entire clip" from tracks
  and reports ball-in-crop rising from 49% to 94% of frames after moving from per-detection
  following to whole-clip planning (172 labelled frames, one broadcaster — small).
  — <https://forum.opencv.org/t/using-opencv-camera-motion-compensation-to-track-a-basketball-and-keep-it-in-vertical-video-crops/24773>

---

## Q5. Measuring that camera motion "reads well"

No source offers a validated objective score for virtual-camera quality; the camera papers fall
back on user studies (Gaddam et al.; Chen et al. 2016, pairwise preference with a binomial
test). What exists splits into a fidelity side and a smoothness side, and every serious
treatment reports both because each is trivially optimised alone (a frozen camera is perfectly
smooth; the raw track is perfectly faithful).

**Fidelity / framing**

- **[P]** **Ball-in-crop percentage** — share of frames with the ball inside the crop. Used by
  Supersonics (70% → 74%, dunks 25% → 62%), the OpenCV-forum project (49% → 94%) and, as "ROI
  accuracy", by Kim et al. (<https://arxiv.org/pdf/2306.08206>). For us this is already
  `check_follow` / `test_ball_is_inside_the_crop_over_the_whole_match`; a stricter variant is
  the ball's distance from the crop edge (a margin), which the sources do not report but the
  inclusion-constraint formulations imply.
- **[E]** **Precision loss** — RMS distance between the produced path and a reference path
  (Chen & Carr: RMS pan error in degrees against a human operator). We have no human reference,
  so the only available reference is the ball track itself.

**Smoothness**

- **[E]** **Joint loss = precision + ω·smoothness** (Chen et al., CVPR 2016, evaluated with
  ω = 500), with the two terms plotted separately. The extract does not show the smoothness
  term's formula; stage 2/3 should read it from the paper.
- **[E]** **Derivative norms** — the objectives of 1.3 are themselves metrics: Σ|Δx| or Σ(Δx)²
  (velocity), Σ(Δ²x)² (**acceleration energy**), Σ(Δ³x)² (**jerk energy**), and their L1
  versions. Grundmann's cinematographic reading gives a sparsity metric as well: the fraction of
  frames where velocity, acceleration or jerk is (near) zero, i.e. how much of the path is
  "tripod", "constant pan" or "constant ease".
- **[E]** **Motor-control smoothness measures** (a mature literature on exactly "is this
  movement smooth"):
  - *Dimensionless jerk* and its log, LDLJ = −ln( (T⁵ / v_peak²) · ∫ |d²v/dt²|² dt ). Balasubramanian
    et al.: DLJ and LDLJ "are the only valid jerk-based measures", valid because dimensionless
    (independent of amplitude and duration), but "very sensitive to measurement noise".
  - *SPARC* (spectral arc length): arc length of the normalised Fourier magnitude spectrum of
    the speed profile up to an adaptive cut-off (amplitude threshold 0.05, max 20 Hz).
    A systematic review of 32 metrics found SPARC the only one that responded correctly in all
    simulation tests; it is robust to noise and independent of duration. Reference Python
    implementation: <https://github.com/siva82kb/SPARC>.
  - *Number of velocity peaks* / acceleration zero-crossings — "simple … but lacks sensitivity
    and robustness"; normalising by duration or distance makes it scale-dependent. For a camera
    this is the count of speed-ups, and its sibling, the **number of direction reversals** of the
    crop, is the most direct numeric form of "jitter".
  — Balasubramanian et al., *On the analysis of movement smoothness*, JNER 2015,
  <https://link.springer.com/article/10.1186/s12984-015-0090-9>; Mohamed Refai et al., JNER 2021,
  <https://link.springer.com/article/10.1186/s12984-021-00949-6>; Bayle et al., Sensors 2023,
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC9919347/>; Gulde & Hermsdörfer 2018,
  <https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2018.00615/full>
  Caveat: these were validated on discrete point-to-point reaches, not on continuous following;
  applying them to a 60 s camera path is an extrapolation.
- **[E]** **Frequency-domain check**: stabilisation defines jitter as "high-frequency
  oscillations throughout the camera path"; the share of path-velocity energy above a cut-off is
  a direct measure, and filter choices can be compared by amplitude spectrum (as the eye-tracking
  comparison does: <https://pmc.ncbi.nlm.nih.gov/articles/PMC11219126/>).
- **[E]** **Peak limits** — maximum |velocity| and |acceleration| of the crop in px/s and px/s²
  (the Bagadus and Supersonics parameters turned into assertions).
- **[E]** Stabilisation's own image-based score, ITF (inter-frame transformation fidelity, a
  PSNR between consecutive frames), needs decoded frames, so it belongs in `tests/integration`,
  if anywhere. Mentioned in <https://link.springer.com/article/10.1186/s13640-018-0277-7>.

All of the path-based metrics are a few lines of numpy on the crop-x array and are
deterministic, so they fit `tests/unit/` with synthetic tracks (step, ramp, sinusoid plus noise)
and can be reported per evaluation window by a command.

---

## Q6. Passing through stretches with no data

- **[E]** **The smoother can do the bridging itself.** With zero weights (Whittaker) or skipped
  updates (RTS), the path through a gap is determined by the data on both sides and the penalty
  order: order 1 → straight line between the ends; order 2 → cubic, entering and leaving with
  the surrounding slope; in general degree 2d − 1. Compared with our current straight chord, the
  cubic removes the velocity step at each end of the gap. Eilers states it works "even in large
  stretches". Caveat from the polynomial form: over a long gap a cubic that must match a steep
  entry slope can bulge well away from the chord — and, for us, outside 0..1312 — so the
  frame-bound check matters most exactly here.
  — Eilers 2003; scipy `whittaker_henderson` docs
- **[E]** **A ball that vanishes is usually possessed, and the possessor's track is the best
  estimate.** Ren, Orwell, Jones, Xu: "If the ball was not seen between frames k1 and k2, it was
  most likely because it was occluded by a player possessing it. The trajectory is estimated to
  be that of the player closest to the ball position at frame k1"; if it re-emerges quickly,
  linear interpolation between the two sightings is used instead. They also state the limit:
  "in the limiting case of severely occluded situations lasting for several seconds or more, the
  system will fail." Our tracking file does carry per-frame `players`, so this is available in
  principle; it is a change to the *target*, not to the smoothing, and by the roadmap it is
  outside S-03 (the evaluation windows have 100% ball coverage on purpose).
  — <https://strathprints.strath.ac.uk/29269/1/cviu_text.pdf>; <http://eprints.kingston.ac.uk/id/eprint/7775>
- **[P]/[O]** Other fallbacks seen: forward-predict from recent ball velocity, then player
  centroid (Supersonics, who then found the centroid "drifts off" and switched to following the
  last ball carrier); centre of frame with zoom-out (Lavigne; H2V4Sports "empty shot … in the
  center"). Learned imputation from player trajectories exists (Kim et al., 2023)
  **[needs: learned model]**.
- **Gap in the literature:** nothing found speaks to gaps as long as ours (up to 25.74 s) in a
  virtual-camera context. Runs that long are probably not occlusion but the ball out of play or
  a tracker failure, and the honest reading of Ren et al. is that no trajectory estimate is
  trustworthy there. What the camera should *show* for 25 s without a ball is a product question
  (hold, drift to players, or cut the window) rather than a filtering one.

---

## Cross-cutting observations

1. **Offline changes the menu.** Every source that compares the two says the same thing: causal
   methods (Kalman filter, springs, exponential follow, rate limiters) are chosen for real-time
   use and pay for it in lag; with the whole path known, zero-phase filters, smoothers and
   whole-trajectory optimisation are available and strictly better informed.
2. **Linear, uniform smoothing has one known failure**: one strength for the whole clip either
   leaves jitter in calm play or cuts corners in fast play. The literature's remedies are
   adaptivity, L1 penalties, or hard inclusion constraints.
3. **L2 versus L1 is an aesthetic choice, and the sources disagree on which is right for
   following.** Grundmann and Gandhi argue L1 (static / constant-pan / eased segments) is what
   professional footage looks like, and that L2 "drifts". Their material is handheld video and
   stage recordings, where long static shots are natural. The one soccer-specific observation
   (Chen et al.: operators pan in straight lines with sharp corrections) also favours L1-like
   paths. Against that, the L2 family is closed-form, banded, deterministic by construction and
   available in scipy today.
4. **Determinism.** Convolutions, `filtfilt`, banded solves and the RTS recursions are
   fixed-sequence floating-point computations with no randomness. Iterative convex solvers
   (interior point, ADMM, simplex/HiGHS) are deterministic too but their result depends on
   tolerances, iteration limits and library version; byte-identical output across scipy versions
   is a question for stage 2, not something the web sources address.
5. **Sampling.** The path is computed from 16.67 Hz samples and rendered at 50 fps. Smoothing
   splines and RTS smoothers produce a function/state that can be evaluated at the frame times
   directly; discrete filters and the Whittaker smoother produce values at sample times and need
   a separate (smooth) upsampling step. None of the sources discuss this; it follows from the
   formulations.

---

## Candidate techniques (for stage 2 and 3 — not a choice)

| # | Technique | One-sentence assessment for our case |
| --- | --- | --- |
| 1 | **Whittaker / Hodrick–Prescott penalised least squares** (order 2 or 3, per-sample weights) | Strongest all-round fit on paper: whole-trajectory, zero lag, one banded solve, native weights (answers Q3 directly), bridges gaps by itself, no edge loss; its weakness is corner rounding from the L2 penalty and a single global λ. |
| 2 | **Weighted cubic smoothing spline** | Mathematically the continuous twin of #1 with the same weights and λ, plus a function that can be evaluated at 50 fps frame times directly; same L2 corner rounding. |
| 3 | **Zero-phase low-pass (Butterworth via forward–backward)** | Simplest zero-lag option with a cut-off in Hz that is easy to reason about; no weights, no gap handling, edge transients on 60 s windows need care. |
| 4 | **Savitzky–Golay (centred)** | Zero-lag and better at keeping peaks than a plain average, with precedent in sports camera work (0.5 s window); weak stop-band attenuation means residual jitter, and it takes no weights. |
| 5 | **Gaussian kernel (fixed or adaptive sigma)** | The stabilisation literature's default and trivially deterministic; fixed sigma is the documented "cuts the peak" case, adaptive sigma fixes that at the cost of a second tuning rule. |
| 6 | **RTS (Kalman) smoother, constant-velocity or constant-acceleration model** | Offline, zero lag, per-sample measurement variance and skipped updates express confidence and gaps exactly, and yields velocity for free; equivalent in effect to #1/#2 but must be hand-written (about 40 lines) and has two noise parameters instead of one λ. |
| 7 | **ℓ1 trend filtering** (L1 on second differences) | Produces straight pans with sharp, sparse corrections — the shape human soccer operators were observed to produce; needs an LP/QP solver, has a known level bias, and corners with zero easing may read as mechanical. |
| 8 | **L1-optimal camera path with inclusion constraints** (Grundmann / Gandhi: L1 on 1st+3rd or 1st–3rd differences, ball-in-crop and frame bounds as hard constraints) | The only candidate that *guarantees* ball-in-frame and the right-edge bound instead of checking them afterwards, and the one built for "reads as cinematography"; heaviest to implement and the one with open solver/determinism questions. |
| 9 | **L2 path with hard inclusion constraints** (QP: #1's objective plus ball-in-crop bounds) | A middle route — smooth as #1 wherever the ball is safely inside, forced to move only when a bound binds; needs a bounded least-squares/QP route in scipy. |
| 10 | **Velocity/acceleration-limited follower with dead zone** (Schmitt trigger, kinematic caps), run with look-ahead | Proven in real-time soccer and cheap, with parameters in physical units; inherently causal, so lag and overshoot are managed rather than removed, and it wastes the fact that we know the future. |
| 11 | **Spring–damper / exponential follow / One-Euro-style adaptive low-pass** | Listed for completeness: designed for streaming, lag is inherent; no advantage offline over #3–#6. |
| 12 | **Piecewise low-degree polynomial path fitting** (AutoFlip's stationary / pan / track) | Gives very calm shots for short scenes; a single polynomial cannot follow 60 s of play, so it would need segmentation, which is its own problem. |

Behaviours worth carrying into any choice (they are orthogonal to the filter): a **dead zone**
so small ball motion moves nothing; an **inclusion margin** instead of exact centring; **clamp
inside the method**, not after it; **velocity and acceleration peaks as assertions**.

Out of bounds for the product, recorded so they are not rediscovered: learned camera planners
(Chen & Carr; recurrent decision trees) **[needs: learned model]**; learned ball imputation
(Kim et al.) **[needs: learned model]**; detector/tracker stacks (YOLO, Mixformer)
**[needs: GPU, learned model]** — upstream of this repository anyway.

---

## Libraries and modules for stage 2 (Context7)

Already in the stack: **numpy**, **scipy**. Stage 2 should confirm signatures, defaults, edge
handling and — for each — whether output is bit-reproducible, against the scipy version pinned
in `uv.lock`.

| Library · module | Functions to look up | Why |
| --- | --- | --- |
| `scipy.signal` | `whittaker_henderson` (seen in the SciPy **1.18** manual; lock pins 1.18.1 but `pyproject.toml` allows `>=1.14` — **find the release that added it**; `lamb`, `order`, `weights`, REML default) | Candidate 1 in one call, with weights and gap interpolation. |
| `scipy.signal` | `butter` (with `output="sos"`), `sosfiltfilt`, `filtfilt` (`padtype`, `padlen`, `method="gust"`) | Candidate 3; edge behaviour on short windows. |
| `scipy.signal` | `savgol_filter` (`mode`: `interp`/`mirror`/`nearest`, `deriv`, `delta`), `savgol_coeffs` | Candidate 4; also derivatives for metrics. |
| `scipy.signal` | `find_peaks` (`prominence`), `periodogram` / `welch` | Metrics: velocity peaks, high-frequency energy share. |
| `scipy.ndimage` | `gaussian_filter1d` (`mode`, `truncate`), `uniform_filter1d` | Candidate 5 and boundary modes. |
| `scipy.interpolate` | `make_smoothing_spline` (`w`, `lam`, GCV default), `make_splrep` / `splrep` / `UnivariateSpline` (`w`, `s` — note squared-weights convention), `BSpline` (`derivative`, evaluation at arbitrary t) | Candidate 2; evaluation at 50 fps; velocity/acceleration from the spline. |
| `scipy.interpolate` | `PchipInterpolator`, `CubicSpline`, `make_interp_spline` | Upsampling a 16.67 Hz path to 50 fps without overshoot; replacement for the linear interpolation in today's `crop_path`. |
| `scipy.linalg` | `solveh_banded`, `solve_banded`, `cholesky_banded` | Hand-written Whittaker/HP (candidate 1 if `whittaker_henderson` is unavailable; needed for order 3 or custom penalties) and banded RTS-equivalent solves. |
| `scipy.sparse` / `scipy.sparse.linalg` | `diags`/`diags_array`, `spsolve`, `splu` | Sparse alternative to the banded route; difference-operator construction. |
| `scipy.optimize` | `linprog` (`method="highs"`), `milp` not needed | Candidates 7 and 8 as linear programmes; check problem-size limits (a 60 s window is ~1 000 samples / 3 000 frames) and reproducibility of HiGHS. |
| `scipy.optimize` | `lsq_linear` (`bounds`, `method="bvls"`/`"trf"`), `minimize(method="trust-constr")`, `LinearConstraint`, `Bounds` | Candidate 9 (bounded least squares = L2 path with ball-in-crop bounds). |
| `numpy` | `convolve`, `gradient`, `diff`, `interp`, `fft.rfft`, `lib.stride_tricks.sliding_window_view`, `clip` | Metrics (derivative energies, reversals, SPARC), dead zone and rate-limit recursions. |

Not in the stack — look up only to decide whether they are worth a dependency (each would need
to pass the scope guards in `CLAUDE.md`):

| Library | What it would give | Note |
| --- | --- | --- |
| `cvxpy` (+ OSQP / Clarabel / SCS) | Direct expression of candidates 7–9 exactly as the papers write them | Pulls in compiled solvers; determinism across versions unknown. |
| `filterpy` (`kalman.KalmanFilter.rts_smoother`) or `pykalman` | Ready RTS smoother with missing-value support | Candidate 6 is small enough to write in numpy; a dependency is hard to justify. |
| `statsmodels` (`tsa.filters.hp_filter.hpfilter`, `tsa.statespace` with NaN handling) | HP filter and a state-space smoother | Heavy dependency for two functions scipy largely covers. |
| `pybaselines` / `pentapy` | Banded Whittaker solvers with weights | Reference implementation to read rather than depend on. |

---

## Open points handed to the later stages

1. **Open Roadmap Question 1** is narrowed but not closed: the literature says a
   straight-line-interpolated sample carries no independent information and should be
   zero-weighted (or the gap passed through), and that convolution filters cannot do this.
   Whether it changes the visible result on runs of ≤ 2.64 s must be measured (stage 3 / plan):
   weight 1 vs reduced vs 0 on both evaluation windows.
2. **L2 or L1** — calm rounded motion or straight pans with sharp corrections — cannot be
   settled by reading; it needs rendered clips of both on the evaluation windows.
3. **Check or constrain**: keep `check_follow` as a post-hoc gate on an unconstrained smoother,
   or make ball-in-crop and 0 ≤ x ≤ 1312 constraints of the optimisation (candidates 8, 9).
4. **Which numbers become assertions**: ball-in-crop (exists), plus a subset of acceleration
   energy, jerk energy / LDLJ, SPARC, direction reversals per minute, peak velocity and
   acceleration. None has a published "good" threshold for camera paths; thresholds would have
   to come from the raw S-02 path as a baseline to beat.
5. **SciPy version**: `scipy.signal.whittaker_henderson` appears in the 1.18 manual and
   `uv.lock` pins scipy 1.18.1 (read from the lock file, the function was not imported), while
   `pyproject.toml` allows `>=1.14`. Stage 2 should find the release that introduced it; relying
   on it would mean raising the lower bound.
6. **Sources not read in full** that stage 2/3 may want: the smoothness-loss definition in Chen
   et al. (CVPR 2016); the "adaptive trigger" model in Gaddam et al. (TOMM 2015); Jianhui Chen's
   thesis chapter on optimising the camera trajectory "in overlapped temporal windows"
   (<http://hdl.handle.net/2429/66791>).
