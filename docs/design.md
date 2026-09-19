# Jev / Trader design spec

Reference: design-concept.png (built-in image generator, full dashboard).
Prompt: Korean BTC/USDT paper trading research terminal; charcoal background,
lime accent, flat bordered panels, top history/live tabs, date/strategy toolbar,
four account metrics, price chart plus decision panel, replay controls,
equity comparison and decision/fill ledger.

Tokens: background #101214, surface #14181b, border #292e33, text #eef1f4,
muted #98a3af, accent #c5ef71, sell #ef8c83. No gradients, imagery or shadows.
Typography: Segoe UI / Malgun Gothic for Korean UI, Cascadia Code / Consolas
for tabular figures. Title 27px; panel titles 17px; controls 13px; metadata 12px.
24px page margin, 14px panel gap, 20px panel inset, 6px corners.

Components: Header, setup toolbar, Metrics, PriceChart, DecisionPanel,
Playback, EquityChart, Journal. Desktop top chart 2:1; lower panels 1:1.
Mobile stacks panels and wraps settings. All controls and charts are native code.

Allowed copy: reference labels plus functional necessities: UTC labels, end-date
exclusive notice, Jev call cap, data-loading and error feedback, saved experiment
selector, export, new experiment, actual API/key status, live connection and stale
quote status, baseline rule legend. Dynamic data replaces illustrative values.
No fabricated probabilities or reasoning for the rule strategy.

Intentional deviations: all timestamps use UTC consistently (reference mixes KST),
initial state is empty until real data is loaded, rule probabilities are absent,
settings/empty/saved-run states added for required functionality, a line price chart
as requested in the brief, baseline rule series added to comparison, local polling
every 5 seconds for live quotes rather than a WebSocket stream in this first version.
