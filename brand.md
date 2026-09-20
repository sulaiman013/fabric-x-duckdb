# Brand

One file next to the folders. Read it before every render, so the look is
settled before the first frame is drawn and the review round judges the motion
rather than the colours.

## Colors

```
primary:    #35AE00   leaf green. the only accent.
headings:   #161D11   near black, warm
body:       #3F4A38   dark grey green
background: #F2FAEB   paper
stage:      #0C110A   the one dark room, for the two real artifacts
```

Three states, and nothing else carries colour:

```
green  #1B6B00 ink  flow, and good
amber  #8F5700 ink  a one-off, or a scheduled path
red    #AE2523 ink  bad. rare, so a failure reads as an event.
```

Vendor colour appears only on a vendor mark.

## Fonts

```
headline:  Newsreader 400, italic for the one emphasised phrase
body:      Plus Jakarta Sans 400 and 600
code:      JetBrains Mono, for every figure and every identifier
```

## Voice

Short sentences. Plain words. No hype. Numbers over adjectives.

Every figure on screen is read out of the run's own evidence: `UAT.json`,
`README.md`, or the script that produced it. If a number cannot be traced to
one of those, it does not go on screen.

Concede once, out loud, where the design loses. A film that never concedes
reads as a sales deck.

## Never

- gradients as decoration
- more than one accent
- content type smaller than 20 px in video. The one exception is the 13 px
  uppercase mono kicker, which is a label rather than something to read, and
  it is deliberate. A figure is never a kicker.
- em dashes or en dashes
- a figure that is not in `UAT.json`, `README.md` or `scripts/`
- a screenshot cover-fitted past legibility
- a lookalike where the real artifact exists

## Motion

Named moves only, from `video/src/motion/library.ts`. Nothing longer than
1.2 seconds. A hold is a beat, not a gap.
