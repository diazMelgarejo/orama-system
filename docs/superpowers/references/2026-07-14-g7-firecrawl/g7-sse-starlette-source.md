[Skip to content](https://github.com/sysid/sse-starlette/blob/main/sse_starlette/sse.py#start-of-content)

You signed in with another tab or window. [Reload](https://github.com/sysid/sse-starlette/blob/main/sse_starlette/sse.py) to refresh your session.You signed out in another tab or window. [Reload](https://github.com/sysid/sse-starlette/blob/main/sse_starlette/sse.py) to refresh your session.You switched accounts on another tab or window. [Reload](https://github.com/sysid/sse-starlette/blob/main/sse_starlette/sse.py) to refresh your session.Dismiss alert

{{ message }}

[sysid](https://github.com/sysid)/ **[sse-starlette](https://github.com/sysid/sse-starlette)** Public

- [Notifications](https://github.com/login?return_to=%2Fsysid%2Fsse-starlette) You must be signed in to change notification settings
- [Fork\\
65](https://github.com/login?return_to=%2Fsysid%2Fsse-starlette)
- [Star\\
838](https://github.com/login?return_to=%2Fsysid%2Fsse-starlette)


## Collapse file tree

## Files

main

Search this repository(forward slash)` forward slash/`

/

# sse.py

Copy path

Blame

More file actions

Blame

More file actions

## Latest commit

[![sysid](https://avatars.githubusercontent.com/u/6587571?v=4&size=40)](https://github.com/sysid)[sysid](https://github.com/sysid/sse-starlette/commits?author=sysid)

[refactor(sse): re-sync EventSourceResponse with Starlette StreamingRe…](https://github.com/sysid/sse-starlette/commit/391f79410d4b8e5aa7ad76378faf0a0d6c614fd9)

Open commit details

3 months agoApr 26, 2026

[391f794](https://github.com/sysid/sse-starlette/commit/391f79410d4b8e5aa7ad76378faf0a0d6c614fd9) · 3 months agoApr 26, 2026

## History

[History](https://github.com/sysid/sse-starlette/commits/main/sse_starlette/sse.py)

Open commit details

[View commit history for this file.](https://github.com/sysid/sse-starlette/commits/main/sse_starlette/sse.py) History

502 lines (414 loc) · 19.1 KB

/

# sse.py

Copy path

Top

## File metadata and controls

- Code

- Blame


502 lines (414 loc) · 19.1 KB

[Raw](https://github.com/sysid/sse-starlette/raw/refs/heads/main/sse_starlette/sse.py)

Copy raw file

Download raw file

You must be signed in to make or propose changes

More edit options

Open symbols panel

Edit and raw actions

1

2

3

4

5

6

7

8

9

10

11

12

13

14

15

16

17

18

19

20

21

22

23

24

25

26

27

28

29

30

31

32

33

34

35

36

37

38

39

40

41

42

43

44

45

46

47

48

49

50

51

52

53

54

55

56

57

58

59

60

61

62

63

64

65

66

67

68

69

70

71

72

73

74

75

76

77

78

79

80

81

82

83

84

85

86

87

88

89

90

91

92

93

94

95

96

97

98

99

100

101

102

103

104

105

106

107

108

109

110

111

112

113

114

115

116

117

118

119

120

121

122

123

124

125

126

127

128

129

130

131

132

133

134

135

136

137

138

139

140

141

142

143

144

145

146

147

148

149

150

151

152

153

154

155

156

157

158

159

160

161

162

163

164

165

166

167

168

169

170

171

172

173

174

175

176

177

178

179

180

181

182

183

184

185

186

187

188

189

190

191

192

193

194

195

196

197

198

199

200

201

202

203

204

205

206

207

208

209

210

211

212

213

214

215

216

217

218

219

220

221

222

223

224

225

226

227

228

229

230

231

232

233

234

235

236

237

238

239

240

241

242

243

244

245

246

247

248

249

250

251

252

253

254

255

256

257

258

259

260

261

262

263

264

265

266

267

268

269

270

271

272

273

274

275

276

277

278

279

280

281

282

283

284

285

286

287

288

289

290

291

292

293

294

295

296

297

298

299

300

301

302

303

304

305

306

307

308

309

310

311

312

313

314

315

316

317

318

319

320

321

322

323

324

325

326

327

328

329

330

331

332

333

334

335

336

337

338

339

340

341

342

343

344

345

346

347

348

349

350

351

352

353

354

355

356

357

358

359

360

361

362

363

364

365

366

367

368

369

370

371

372

373

374

375

376

377

378

379

380

381

382

383

384

385

386

387

388

389

390

391

392

393

394

395

396

397

398

399

400

401

402

403

404

405

406

407

408

409

410

411

412

413

414

415

416

417

418

419

420

421

422

423

424

425

426

427

428

429

430

431

432

433

434

435

436

437

438

439

440

441

442

443

444

445

446

447

448

449

450

451

452

453

454

455

456

457

458

459

460

461

462

463

464

465

466

467

468

469

470

471

472

473

474

475

476

477

478

479

480

481

482

483

484

485

486

487

488

489

490

491

492

493

494

495

496

497

498

499

500

501

502

"""Server-Sent Events response for Starlette / FastAPI.

Intentional divergence from \`\`starlette.responses.StreamingResponse\`\`

\-\-\------------------------------------------------------------------

\`\`EventSourceResponse\`\` is modelled on Starlette's \`\`StreamingResponse\`\` and

re-syncs most of its behaviour (WebSocket denial, \`\`collapse\_excgroups()\`\`

around the task group, \`\`memoryview\`\` chunk handling). The following points

are deliberate divergences — DO NOT "fix" them without reading the rationale:

1\. ASGI \`\`spec\_version >= 2.4\`\` fast path is NOT adopted.

Upstream short-circuits to \`\`await stream\_response(send)\`\` and converts

\`\`OSError\`\` into \`\`ClientDisconnect\`\`, skipping \`\`listen\_for\_disconnect\`\`.

We keep \`\`\_listen\_for\_disconnect\`\` running because it

(a) invokes \`\`client\_close\_handler\_callable\`\` on disconnect,

(b) flips \`\`self.active = False\`\` so \`\`\_ping\`\` and the cooperative

shutdown grace loop exit promptly.

Adopting the upstream fast path would regress both features.

2\. \`\`\_wrap\_websocket\_denial\_send\`\` is inlined in this module rather than

inherited from \`\`starlette.responses.Response\`\`. The helper landed on

Starlette \`\`main\`\` after our minimum pin (\`\`starlette>=0.41.3\`\`); inline

until the floor moves past the release that contains it.

3\. \`\`collapse\_excgroups()\`\` is vendored in \`\`sse\_starlette.\_utils\`\` rather

than imported from \`\`starlette.\_utils\`\` (private module).

"""

importasyncio

importlogging

importsignal

importthreading

fromdataclassesimportdataclass, field

fromdatetimeimportdatetime, timezone

fromtypingimport (

Any,

AsyncIterable,

Awaitable,

Callable,

Coroutine,

Iterator,

Mapping,

Optional,

Set,

Union,

)

importanyio

fromstarlette.backgroundimportBackgroundTask

fromstarlette.concurrencyimportiterate\_in\_threadpool

fromstarlette.datastructuresimportMutableHeaders

fromstarlette.responsesimportResponse

fromstarlette.typesimportReceive, Scope, Send, Message

fromsse\_starlette.\_utilsimportcollapse\_excgroups

fromsse\_starlette.eventimportServerSentEvent, ensure\_bytes

logger=logging.getLogger(\_\_name\_\_)

@dataclass

class\_ShutdownState:

"""Per-thread state for shutdown coordination.

Issue #152 fix: Uses threading.local() instead of ContextVar to ensure

one watcher per thread rather than one per async context.

"""

events: Set\[anyio.Event\] =field(default\_factory=set)

watcher\_started: bool=False

\# Each thread gets its own shutdown state (one event loop per thread typically)

\_thread\_state=threading.local()

def\_get\_shutdown\_state() ->\_ShutdownState:

"""Get or create shutdown state for the current thread."""

state=getattr(\_thread\_state, "shutdown\_state", None)

ifstateisNone:

state=\_ShutdownState()

\_thread\_state.shutdown\_state=state

returnstate

def\_get\_uvicorn\_server():

"""

Try to get uvicorn Server instance via signal handler introspection.

When uvicorn registers signal handlers, they're bound methods on the Server instance.

We can retrieve the Server from the handler's \_\_self\_\_ attribute.

Returns None if:

\- Not running under uvicorn

\- Signal handler isn't a bound method

\- Any introspection fails

"""

try:

handler=signal.getsignal(signal.SIGTERM)

ifhasattr(handler, "\_\_self\_\_"):

server=handler.\_\_self\_\_

ifhasattr(server, "should\_exit"):

returnserver

exceptException:

pass

returnNone

asyncdef\_shutdown\_watcher() ->None:

"""

Poll for shutdown and broadcast to all events in this context.

One watcher runs per thread (event loop). Checks two shutdown sources:

1\. AppStatus.should\_exit - set when our monkey-patch works

2\. uvicorn Server.should\_exit - via signal handler introspection (Issue #132 fix)

When either becomes True, signals all registered events.

"""

state=\_get\_shutdown\_state()

uvicorn\_server=\_get\_uvicorn\_server()

try:

whileTrue:

\# Check our flag (monkey-patch worked or manually set)

ifAppStatus.should\_exit:

break

\# Check uvicorn's flag directly (monkey-patch failed - Issue #132)

if (

AppStatus.enable\_automatic\_graceful\_drain

anduvicorn\_serverisnotNone

anduvicorn\_server.should\_exit

):

AppStatus.should\_exit=True\# Sync state for consistency

break

awaitanyio.sleep(0.5)

\# Shutdown detected - broadcast to all waiting events

foreventinlist(state.events):

event.set()

finally:

\# Allow watcher to be restarted if loop is reused

state.watcher\_started=False

def\_ensure\_watcher\_started\_on\_this\_loop() ->None:

"""Ensure the shutdown watcher is running for this thread (event loop)."""

state=\_get\_shutdown\_state()

ifnotstate.watcher\_started:

state.watcher\_started=True

try:

loop=asyncio.get\_running\_loop()

loop.create\_task(\_shutdown\_watcher())

exceptRuntimeError:

\# No running loop - shouldn't happen in normal use

state.watcher\_started=False

def\_wrap\_websocket\_denial\_send(send: Send) ->Send:

"""Mirror of \`\`starlette.responses.Response.\_wrap\_websocket\_denial\_send\`\`.

Divergence #2 (see module docstring): inlined because the helper landed

on Starlette \`\`main\`\` (commit 9ee9519) after our minimum pin

\`\`starlette>=0.41.3\`\`. Drop this once the floor moves past the release

that contains it.

"""

asyncdefwrapped(message: Message) ->None:

message\_type=message\["type"\]

ifmessage\_typein {"http.response.start", "http.response.body"}:

message= {\*\*message, "type": "websocket."+message\_type}

awaitsend(message)

returnwrapped

classSendTimeoutError(TimeoutError):

pass

classAppStatus:

"""Helper to capture a shutdown signal from Uvicorn so we can gracefully terminate SSE streams."""

should\_exit=False

enable\_automatic\_graceful\_drain=True

original\_handler: Optional\[Callable\] =None

@staticmethod

defdisable\_automatic\_graceful\_drain():

"""

Prevent automatic SSE stream termination on server shutdown.

WARNING: When disabled, you MUST set AppStatus.should\_exit = True

at some point during shutdown, or streams will never close and the

server will hang indefinitely (or until uvicorn's graceful shutdown

timeout expires).

"""

AppStatus.enable\_automatic\_graceful\_drain=False

@staticmethod

defenable\_automatic\_graceful\_drain\_mode():

"""

Re-enable automatic SSE stream termination on server shutdown.

This restores the default behavior where SIGTERM triggers immediate

stream draining. Call this to undo a previous call to

disable\_automatic\_graceful\_drain().

"""

AppStatus.enable\_automatic\_graceful\_drain=True

@staticmethod

defhandle\_exit(\*args, \*\*kwargs):

ifAppStatus.enable\_automatic\_graceful\_drain:

AppStatus.should\_exit=True

ifAppStatus.original\_handlerisnotNone:

AppStatus.original\_handler(\*args, \*\*kwargs)

try:

fromuvicorn.mainimportServer

AppStatus.original\_handler=Server.handle\_exit

Server.handle\_exit=AppStatus.handle\_exit\# type: ignore

exceptImportError:

logger.debug(

"Uvicorn not installed. Graceful shutdown on server termination disabled."

)

Content=Union\[str, bytes, dict, ServerSentEvent, Any\]

SyncContentStream=Iterator\[Content\]

AsyncContentStream=AsyncIterable\[Content\]

ContentStream=Union\[AsyncContentStream, SyncContentStream\]

classEventSourceResponse(Response):

"""Streaming response implementing the SSE (Server-Sent Events) specification.

Args:

content: Async iterable or sync iterator yielding SSE event data.

status\_code: HTTP status code. Default: 200.

headers: Additional HTTP headers.

media\_type: Response media type. Default: "text/event-stream".

background: Background task to run after response completes.

ping: Ping interval in seconds (0 to disable). Default: 15.

sep: Line separator for SSE messages ("\\\r\\\n", "\\\r", or "\\\n").

ping\_message\_factory: Callable returning custom ping ServerSentEvent.

data\_sender\_callable: Async callable for push-based data sending.

send\_timeout: Timeout in seconds for individual send operations.

client\_close\_handler\_callable: Async callback on client disconnect.

shutdown\_event: Optional \`\`anyio.Event\`\` set by the library when server

shutdown is detected. Generators can watch this event to send farewell

messages and exit cooperatively instead of receiving CancelledError.

shutdown\_grace\_period: Seconds to wait after setting \`\`shutdown\_event\`\`

before force-cancelling the generator. Must be >= 0. Should be less

than your ASGI server's graceful shutdown timeout. Default: 0

(immediate cancel, identical to pre-v3.3.0 behavior).

"""

DEFAULT\_PING\_INTERVAL=15

DEFAULT\_SEPARATOR="\\r\\n"

def\_\_init\_\_(

self,

content: ContentStream,

status\_code: int=200,

headers: Optional\[Mapping\[str, str\]\] =None,

media\_type: str="text/event-stream",

background: Optional\[BackgroundTask\] =None,

ping: Optional\[int\] =None,

sep: Optional\[str\] =None,

ping\_message\_factory: Optional\[Callable\[\[\], ServerSentEvent\]\] =None,

data\_sender\_callable: Optional\[\
\
Callable\[\[\], Coroutine\[None, None, None\]\]\
\
\] =None,

send\_timeout: Optional\[float\] =None,

client\_close\_handler\_callable: Optional\[\
\
Callable\[\[Message\], Awaitable\[None\]\]\
\
\] =None,

shutdown\_event: Optional\[anyio.Event\] =None,

shutdown\_grace\_period: float=0,

) ->None:

\# Validate separator

ifsepnotin (None, "\\r\\n", "\\r", "\\n"):

raiseValueError(f"sep must be one of: \\\r\\\n, \\\r, \\\n, got: {sep}")

self.sep=seporself.DEFAULT\_SEPARATOR

\# If content is sync, wrap it for async iteration

ifisinstance(content, AsyncIterable):

self.body\_iterator=content

else:

self.body\_iterator=iterate\_in\_threadpool(content)

self.status\_code=status\_code

self.media\_type=self.media\_typeifmedia\_typeisNoneelsemedia\_type

self.background=background

self.data\_sender\_callable=data\_sender\_callable

self.send\_timeout=send\_timeout

\# Build SSE-specific headers.

\_headers=MutableHeaders()

ifheadersisnotNone: \# pragma: no cover

\_headers.update(headers)

\# "The no-store response directive indicates that any caches of any kind (private or shared)

\# should not store this response."

\# -- https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control

\# allow cache control header to be set by user to support fan out proxies

\# https://www.fastly.com/blog/server-sent-events-fastly

\_headers.setdefault("Cache-Control", "no-store")

\# mandatory for servers-sent events headers

\_headers\["Connection"\] ="keep-alive"

\_headers\["X-Accel-Buffering"\] ="no"

self.init\_headers(\_headers)

self.ping\_interval=self.DEFAULT\_PING\_INTERVALifpingisNoneelseping

self.ping\_message\_factory=ping\_message\_factory

self.client\_close\_handler\_callable=client\_close\_handler\_callable

\# Cooperative shutdown (Issue #167): Allow generators to send farewell

\# events before force-cancellation. The grace period should be less than

\# your ASGI server's graceful shutdown timeout (e.g. uvicorn's

\# --timeout-graceful-shutdown), otherwise the process is killed before

\# the grace period expires.

ifshutdown\_grace\_period<0:

raiseValueError("shutdown\_grace\_period must be >= 0")

self.\_shutdown\_event=shutdown\_event

self.\_shutdown\_grace\_period=shutdown\_grace\_period

self.active=True

\# https://github.com/sysid/sse-starlette/pull/55#issuecomment-1732374113

self.\_send\_lock=anyio.Lock()

@property

defping\_interval(self) ->Union\[int, float\]:

returnself.\_ping\_interval

@ping\_interval.setter

defping\_interval(self, value: Union\[int, float\]) ->None:

ifnotisinstance(value, (int, float)):

raiseTypeError("ping interval must be int")

ifvalue<0:

raiseValueError("ping interval must be greater than 0")

self.\_ping\_interval=value

defenable\_compression(self, force: bool=False) ->None:

raiseNotImplementedError("Compression is not supported for SSE streams.")

asyncdef\_stream\_response(self, send: Send) ->None:

"""Send out SSE data to the client as it becomes available in the iterator."""

awaitsend(

{

"type": "http.response.start",

"status": self.status\_code,

"headers": self.raw\_headers,

}

)

asyncfordatainself.body\_iterator:

chunk=ensure\_bytes(data, self.sep)

logger.debug("chunk: %s", chunk)

withanyio.move\_on\_after(self.send\_timeout) ascancel\_scope:

awaitsend(

{"type": "http.response.body", "body": chunk, "more\_body": True}

)

ifcancel\_scopeandcancel\_scope.cancel\_called:

aclose=getattr(self.body\_iterator, "aclose", None)

ifacloseisnotNone:

awaitaclose()

raiseSendTimeoutError()

asyncwithself.\_send\_lock:

self.active=False

awaitsend({"type": "http.response.body", "body": b"", "more\_body": False})

asyncdef\_listen\_for\_disconnect(self, receive: Receive) ->None:

"""Watch for a disconnect message from the client.

Divergence #1 (see module docstring): kept unconditionally instead of

adopting Starlette's ASGI 2.4 \`\`OSError → ClientDisconnect\`\` fast path,

because this loop drives \`\`client\_close\_handler\_callable\`\` and flips

\`\`self.active = False\`\` for \`\`\_ping\`\` and the shutdown grace loop.

"""

whileself.active:

message=awaitreceive()

ifmessage\["type"\] =="http.disconnect":

self.active=False

logger.debug("Got event: http.disconnect. Stop streaming.")

ifself.client\_close\_handler\_callable:

awaitself.client\_close\_handler\_callable(message)

break

@staticmethod

asyncdef\_listen\_for\_exit\_signal() ->None:

"""Wait for shutdown signal via the shared watcher."""

ifAppStatus.should\_exit:

return

\_ensure\_watcher\_started\_on\_this\_loop()

state=\_get\_shutdown\_state()

event=anyio.Event()

state.events.add(event)

try:

\# Double-check after registration

ifAppStatus.should\_exit:

return

awaitevent.wait()

finally:

state.events.discard(event)

asyncdef\_listen\_for\_exit\_signal\_with\_grace(self) ->None:

"""Wait for shutdown signal, then optionally give generator a grace period.

Issue #167: When a shutdown\_event is provided, the library sets it before

returning, giving the generator a chance to send farewell events and exit

cooperatively. The shutdown\_grace\_period controls how long to wait before

force-cancelling via task group cancellation.

"""

awaitself.\_listen\_for\_exit\_signal()

\# Signal the user's generator that shutdown is happening

ifself.\_shutdown\_event:

self.\_shutdown\_event.set()

\# Grace period: let generator finish naturally before force-cancel

ifself.\_shutdown\_grace\_period>0:

withanyio.move\_on\_after(self.\_shutdown\_grace\_period):

whileself.active:

awaitanyio.sleep(0.1)

asyncdef\_ping(self, send: Send) ->None:

"""Periodically send ping messages to keep the connection alive on proxies.

\- frequenccy ca every 15 seconds.

\- Alternatively one can send periodically a comment line (one starting with a ':' character)

"""

whileself.active:

awaitanyio.sleep(self.\_ping\_interval)

sse\_ping= (

self.ping\_message\_factory()

ifself.ping\_message\_factory

elseServerSentEvent(

comment=f"ping - {datetime.now(timezone.utc)}", sep=self.sep

)

)

ping\_bytes=ensure\_bytes(sse\_ping, self.sep)

logger.debug("ping: %s", ping\_bytes)

asyncwithself.\_send\_lock:

ifself.active:

awaitsend(

{

"type": "http.response.body",

"body": ping\_bytes,

"more\_body": True,

}

)

asyncdef\_\_call\_\_(self, scope: Scope, receive: Receive, send: Send) ->None:

"""Entrypoint for Starlette's ASGI contract. We spin up tasks:

\- \_stream\_response to push events

\- \_ping to keep the connection alive

\- \_listen\_for\_exit\_signal to respond to server shutdown

\- \_listen\_for\_disconnect to respond to client disconnect

"""

\# WebSocket denial parity with Starlette's StreamingResponse: a

\# streaming response on a websocket scope must wrap send so message

\# types become \`\`websocket.http.response.\*\`\`.

ifscope\["type"\] =="websocket":

send=\_wrap\_websocket\_denial\_send(send)

\# collapse\_excgroups parity with Starlette's StreamingResponse: anyio

\# v4 wraps task-group failures in ExceptionGroup; user middleware

\# expects the bare exception.

withcollapse\_excgroups():

asyncwithanyio.create\_task\_group() astask\_group:

\# https://trio.readthedocs.io/en/latest/reference-core.html#custom-supervisors

asyncdefcancel\_on\_finish(coro: Callable\[\[\], Awaitable\[None\]\]):

awaitcoro()

task\_group.cancel\_scope.cancel()

task\_group.start\_soon(

cancel\_on\_finish, lambda: self.\_stream\_response(send)

)

task\_group.start\_soon(cancel\_on\_finish, lambda: self.\_ping(send))

task\_group.start\_soon(

cancel\_on\_finish, self.\_listen\_for\_exit\_signal\_with\_grace

)

ifself.data\_sender\_callable:

task\_group.start\_soon(self.data\_sender\_callable)

\# Wait for the client to disconnect last

task\_group.start\_soon(

cancel\_on\_finish, lambda: self.\_listen\_for\_disconnect(receive)

)

ifself.backgroundisnotNone:

awaitself.background()

You can’t perform that action at this time.