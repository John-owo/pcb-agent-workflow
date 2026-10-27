# Case study: an order for a 4-layer GNSS test board

September 2026: a 25 × 36.5 mm 4-layer GNSS breakout, 5 PCBs, 2 of which had top-side assembly done by the factory, with pin headers soldered by hand. Dates are given only as early, mid or late month; late-month events use relative days, with D1 being the day of submission for review. People are referred to by role, and IDs have been removed.

| Date | What was asked | How they answered | Result |
|---|---|---|---|
| Early September | A supercapacitor clearly in stock was removed from the assembly parts library; could it be manually sourced or consigned? | Neither; no restoration date either. On follow-up, they confirmed all supercapacitors and batteries are the same | Revised the design, removing this energy-storage part |
| Early to mid September | Asked the sales contact for a quote and coupon; first lowered the cart amount, then applied with a cart screenshot attached | Issued a coupon with a minimum spend and region limits | Coupon obtained |
| Late D1 | Online customer service: scope of rail removal, price difference, whether a resistor near the board edge is safe, whether review can come before payment | Rails removed on all 5 boards; the difference is the total rail-removal fee, charged separately after review; review before payment is possible | Submitted for review only, not paid |
| D2 | Status chase on PCBA review (stated 10–60 minutes, actually already overnight) | One agent said the engineering email had been sent; another corrected that it had not actually been sent | Engineering email received the next day |
| D3 | Engineering sent questions about pin headers, diodes, LEDs, rails, etc.; replied point by point by number | Reply the next day: waiting for final DFM | PCB/PCBA review passed |
| D6 | Single-question email: where is the final DFM? | DFM is done only after payment | User paid |
| D6 evening | Both orders cancelled, reason given as internal compliance assessment. Asked the reason, whether they could be reinstated, and the lead time | They admitted a colleague's operating error and offered a small compensation coupon; after four follow-up points they refused to reinstate the original order, could not ship before the holiday, and only promised priority handling after the holiday | Reached the "final refusal" stop condition |
| D6–D7 | Reordered with the same files, with all engineering clarifications in the order remarks; asked the sales contact to help coordinate | No record of a reply from the sales contact | New order paid |
| D7 | Emailed the engineering contact to take ownership; at the same time chased DFM in chat, asking four items at once | Email only reassured, no timeline; chat was transferred to engineering, who replied only "sure", then it closed automatically | Still no deadline |
| D7 afternoon | — | Rail-removal fee waived; sent the PCB production file (please confirm within 48 hours) and PCBA parts placement confirmation (goes straight to production if not confirmed within 72 hours) | Entered manual review |
| D7 evening | Sent a pure technical clarification on the production file: used coordinates to describe a resistor, via shifts, transistor orientation, and the placement centre of the RF connector (J1) | Point-by-point reply with images: added a protective note; vias were moved slightly for via plugging; transistor corrected per silkscreen pin 1; the J1 web readout is the placement centre | Sent another email asking only about the 0.89 mm difference between the J1 readout and the mechanical centre |
| D10 | — | — | User handled the J1 issue themselves. The original order's refund and compliance flag were still unanswered as of the last record |

## Lessons from this case

- What worked: a self-contained first message, a boundary statement in every email, engineering questions written with coordinates, following up only on the remaining point, writing requirements into the order remarks.
- What did not work: mixing refund and compliance questions into the end of a long email, ending a conversation with only "we will send an email".
- For details, see [pitfalls.md](pitfalls.md) and [templates.md](templates.md).
