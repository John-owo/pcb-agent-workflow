# Message templates

Generalized from emails that were actually sent and got replies. `<...>` marks fields to replace. Before sending, get the user's consent per the hard rules in SKILL.md.

ID fields: `<BATCH_ID>` is the ID of the whole order (batch), `<PCB_ID>`/`<PCBA_ID>` are the sub-order IDs under it, and `<ORDER_ID>` is used in emails that concern a single order only (cancellation, refund).

## A. Status chase on a review or DFM

```
Subject: Request for review status and owner — <BATCH_ID>

Hello,

For order <BATCH_ID> (PCB <PCB_ID> / PCBA <PCBA_ID>): I checked the order page at
<TIME TZ>. The detailed status has been <STATUS> since <TIME>, while the site states
<STATED_DURATION>.

Please confirm:
1. The current stage, and any blocker or missing information from my side.
2. The responsible person or team.
3. Where the report will appear and when I can review it.
4. The earliest realistic dispatch date after my approval.

If no completion time is available yet, please give a named owner and a specific
next-update time (<TZ>).

This is not approval of DFM/production, design changes or extra fees. Please keep
manual confirmation.

Thank you,
<NAME>
```

## B. Requesting reinstatement of a cancelled order

```
Subject: Cancelled order <ORDER_ID> — reinstatement and recovery plan

Hello <ROLE>,

Thank you for confirming the cancellation was <CAUSE>. The order was submitted on
<DATE>, approved on <DATE> and paid on <DATE>.

Before I decide on a new order, please clarify:
1. Can the original order be reinstated? If not, can the completed reviews and
   engineering clarifications be carried over to a new order?
2. Is any compliance issue still outstanding, given the stated reason?
3. Given <HOLIDAY_DATES>, what are the earliest review, dispatch and delivery dates,
   and can this case be prioritized?
4. What is the status of the original payment, and would a new order require another
   payment?

I have not yet accepted <COMPENSATION> as a resolution or authorized a new order.
Please keep all manual confirmation steps.

Thank you,
<NAME>
```

## C. Technical clarification on the production file

```
Subject: Re: <THREAD> — engineering clarification before confirmation

Hello <ROLE>,

I have downloaded <FILE> and am reviewing it before final confirmation.

1. <ITEM>: original (<x>, <y>) mm in single-board coordinates; CAM offset
   (+<dx>, +<dy>) mm; observed (<x'>, <y'>) mm. I am not alleging <DEFECT>. Please
   confirm the reason for the change and that <CHECK> still passes.
2. <ITEM>: the viewer readout may be a <cursor / library origin>. Please confirm the
   actual <centre / contacts> with a marked image. Please do not move the part only
   to match a displayed value.

Please reply with the conclusions, the owner and the next-update time (<TZ>).
This is a technical question only, not approval.

Thank you,
<NAME>
```

## D. Quote and coupon request (sales or partner contact)

```
Subject: <PROJECT> — quote and coupon confirmation (no order yet)

Hello <ROLE>,

Following our earlier conversation: draft <DRAFT_ID>, <QTY / SPEC>. The cart shows
<AMOUNTS> (screenshot attached). It does not include <UNQUOTED_ITEMS>.

Please confirm the coupon amount, what it covers (PCB / PCBA / parts / shipping), the
expiry date, any region limits, and whether an order number is needed first. If an
order must exist first, please explain the process. I am not authorizing an order or
payment yet.

Thank you,
<NAME>
```

## E. Asking the factory to take ownership after payment

```
Subject: Re: <THREAD> — replacement order <NEW_ID> paid; please take ownership

Hello <ROLE>,

Payment was received at <TIME TZ>; the detailed status is <STATUS>. New IDs: <IDS>.

Please confirm that you will follow this order, the next update time, and the earliest
review, dispatch and delivery dates. Please refer the engineers to the clarifications
already given on <PREVIOUS_ID>.

Still unanswered: <ITEMS>. Please keep manual confirmation and contact me before any
change or fee.

Thank you,
<NAME>
```

## F. Refund follow-up

This template is derived from experience; the records have no successful case yet. The key is to keep it separate from production progress in its own thread.

```
Subject: Refund status — cancelled order <ORDER_ID> (separate from production follow-up)

Hello,

Order <ORDER_ID> was cancelled on <DATE> after a payment of <AMOUNT>. The coupon has
been returned, but the payment refund has not been confirmed (asked on <DATES>).

Please confirm:
1. The refund amount.
2. The method and destination.
3. The expected completion date.
4. A reference number.

If you cannot answer, please escalate to the responsible team and tell me who will
reply and by when (<TZ>).

Thank you,
<NAME>
```

## Chat opener (online customer service)

Chat has no subject line. Paste the full background in the first message so whoever is in the queue or takes over in rotation understands it directly:

```
Hello. Order <BATCH_ID> (PCB <PCB_ID> / PCBA <PCBA_ID>; previous IDs <OLD_IDS>).
At <TIME TZ> the detailed status is <STATUS>. I have <N> questions:
1. ...
2. ...
If you cannot answer now, please tell me who owns this and when I will get an update
(<TZ>). This is not approval of any change or fee.
```
