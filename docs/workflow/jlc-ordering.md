# JLC ordering and review submission

A checklist from uploading the release package to JLCPCB through confirming the production file after payment. Site rules and prices change; the numbers below were observed 2026-09. Before ordering, go by the official capabilities pages and quote:

- Assembly capabilities: <https://jlcpcb.com/capabilities/pcb-assembly-capabilities>
- PCBA FAQ: <https://jlcpcb.com/help/article/pcb-assembly-faqs>
- Surface finish: <https://jlcpcb.com/help/article/jlcpcb-surface-finish>

If this is your first order and you don't know the process yet, read steps 7 and 8 of [Getting started](../getting-started.md) first: PCB only and solder it yourself, or Economic PCBA with single-side assembly.

For communicating with customer service and engineering, see [skills/jlc-support](../../skills/jlc-support/SKILL.md); for comparing the production file once you receive it, see the [jlc-production-review skill](../../skills/jlc-production-review/SKILL.md).

**Who decides:** uploading files, accepting terms, submitting for review, paying, downloading factory files, confirming the production file or parts placement, and sending messages each require the user's explicit consent every time (status chases and pure technical clarifications have one limited exception; see jlc-support's hard rules). The agent goes as far as preparing files, checking parts matching, and drafting messages.

## 1. Choose a service level

| | Economic | Standard |
|---|---|---|
| Assembly sides | Single side | Single or double side |
| Smallest component | 0402 | 0201 |
| Minimum board or panel size | Per capabilities page | 70 × 70 mm, needs rails and fiducials |

- If you have 0201 or smaller components (for example an ESD diode in a DSN0603 package), you can't choose Economic.
- If the board is smaller than 70 × 70 mm, you can panelize it yourself or have JLC add rails and fiducials. Removing the rails is a separately charged advanced option.
- "5 pcs" is the number of finished boards, not 5 panels. The number of units per panel and the number of panels are set separately in the quote tool.

## 2. Prepare the BOM and CPL

- The BOM needs at least Comment/Value, Designator, Footprint, `LCSC Part #`.
- The CPL contains only designators from the BOM that will actually be assembled. Don't mix in DNP parts, test points, fiducials, or mounting holes.
- The BOM and CPL designator sets must match exactly; compare them once with [check_bom_cpl.py](../../skills/jlc-production-review/scripts/check_bom_cpl.py) before uploading. It also checks JLC column names, duplicate designators, part number format, and coordinates; rotation and polarity still have to be confirmed in the preview.
- Gerber, drill, BOM, CPL, and assembly drawing must come from the same release version.

## 3. After uploading, check parts matching item by item

After the platform matches parts automatically, look at every group:

- Manufacturer, full MPN, C-code, package
- Assembly side, rotation, polarity (look at pin 1 in the preview)
- Live stock and attrition quantity

Where things go wrong:

- **In stock does not mean it can be assembled.** The part may already have been removed from the assembly parts library, and the notice only pops up when you click Select. As of 2026-09, no supercapacitors or batteries could be assembled, not even as consigned parts.
- **Non-standard processes need approval from the factory's engineering review.** For example, a pin header inserted upside down from the bottom side. The site only says THT is supported, not that any orientation is; put it in the remarks when submitting for review and wait for engineering's reply. A rejection is a hard blocker; don't silently switch to soldering it yourself.

## 4. Cutting cost

Real case (4 layers, 25 × 36.5 mm, 5 PCBs, 2 assembled). Both quotes were for 2 assembled boards; the cart total dropped from about USD 174 to about USD 90 thanks to these three things:

- **Top-side assembly only.** The pin headers are soldered by hand after delivery, saving the THT process.
- **Let JLC add rails**, which is cheaper than panelizing yourself.
- **Switch the surface finish to OSP.** PCB quotes for the same board: ENIG with own panel about 46, ENIG with JLC rails about 26, lead-free HASL about 14, OSP about 9 (USD). HASL surfaces are uneven and not suited to very small pads; OSP boards should be soldered soon after unsealing, and the shelf life unopened is about 3 months.

Another common approach is to assemble only as many boards as you need, for example making 5 PCBs and assembling only 2, keeping the rest as spares. The case above was quoted this way from the start.

## 5. Settings before submitting

- **Confirm Production file: Yes**, **Confirm Parts Placement: Yes**. Keep manual confirmation for both.
- **Order remarks** should include all process requirements (rail removal scope, components needing factory engineering review, no automatic confirmation), with the assembly drawing PDF attached. The factory's CAM side can see the remarks.
- **Review Before Payment**: you can submit for review first and pay afterwards. Review hours are working days (Monday to Saturday 9:00–18:00, GMT+8), taking 10 minutes to 4 hours each time.
- **Saving the cart changes its number.** When communicating externally, include both the old and new numbers.
- Customs clearance details and payment are filled in on the website by the user personally; the agent does not handle them.

## 6. Check the amount

- The cart total doesn't necessarily include advanced options. Items marked "not included in Total Price" or "Quote after review" on the quote page are charged after review.
- Coupons can only be applied on the payment page. The face value isn't the actual discount; look at the amount actually paid on the payment page.
- The destination may charge additional taxes or customs clearance fees, per the site's trade terms.

## 7. After payment

1. The status goes roughly Reviewing → Data Preparation → confirmation items (production file, parts placement confirmation) → production. Look at the detailed status, not just the badge at the top of the page.
2. PCBA DFM may only start after payment.
3. When you receive the **PCB production file**: the email asks for confirmation within 48 hours. Compare it following the [jlc-production-review skill](../../skills/jlc-production-review/SKILL.md).
4. When you receive the **PCBA parts placement confirmation**: the email states that production proceeds directly if it's not confirmed within 72 hours. Calculate the deadline as soon as the email arrives, write it in the WORKLOG, and tell the user.
5. Confirming the production file or parts placement is always the user's decision.

## 8. Schedule risks

- Site banners announce factory holidays and recommend ordering 3–5 days in advance.
- The review time shown on the site is not a promise; in 2026-09 it once showed 10–60 minutes and actually took more than a day.
- Even after review approval and payment, the order can still be cancelled. Leave time to reorder.

## 9. Shipping to Taiwan

The following was observed 2026-09 for shipping to Taiwan. Logistics and customs rules change; go by the checkout page, carrier notices, and announcements from the Customs Administration, Ministry of Finance.

**Shipping method**

- For small orders choose **SF Express**. The checkout page estimated 3–5 working days at the time; for a small order of 5 PCBs plus 2 PCBA, shipping was about USD 5.
- Estimate lead time by adding factory production time, factory holidays, and shipping time; don't look only at shipping days.

**Customs clearance details**

- Observed 2026-09: JLC's checkout page lists the **national ID number** used by SF Express for customs clearance as required. This is the platform's field requirement; go by the checkout page each time.
- **When reordering, the customs fields are not carried over from the previous order.** Recheck them at every checkout. If this field is left empty, the order gets stuck before submission.
- The recipient's name must match their ID, and the mobile phone must be able to receive SMS from the carrier or customs.
- **Real-name verification.** After completing the Customs Administration's real-name verification for express consignees, simplified express declarations identify you by name and mobile number, and customs brokers should no longer ask for your national ID number ([Customs Administration real-name verification FAQ](https://web.customs.gov.tw/singlehtml/3150?cntId=cus1_3150_3150_1150)).
- **Advance confirmation of appointment.** From 2026-03-01, simplified-declaration express shipments for individuals appointed online through real-name verification are all subject to "advance confirmation of appointment": the customs broker first pushes the shipment details through the "EZ WAY" app, and only after the recipient checks that it matches the actual purchase and completes the online appointment does the broker file the declaration ([Ministry of Finance announcement, 2026-02-24](https://www.mof.gov.tw/%20/singlehtml/384fb3077bb349ea973e7fc6f13b6974?cntId=87e84e6a6cbc4af9a6608d03c333b06c)). Without confirmation, the shipment stops before declaration.
- When an EZ WAY push notification arrives, the user personally checks the items and amount and decides whether to appoint; the agent does not operate it on their behalf. This project's records did not keep this part of the process, so go by the app and Customs Administration announcements for the actual screens.

**Who fills it in**

- National ID number, shipping address, phone, and payment details are always filled in on the website by the user personally.
- The agent does not read, record, or relay this data, and does not leave it in the WORKLOG or reports.
- Screenshots of the checkout and customs pages almost always contain name, phone, and address; don't put them in any repo. When you need to keep evidence, store screenshots in a private folder on your own computer; the repo and WORKLOG only record in text "filled in by the user".

**Fees**

- JLC's trade terms state that the destination may charge additional taxes or customs clearance fees. The amount you see at checkout is not necessarily the final total.
- Whether tax is charged, and how much, depends on Customs Administration rules and the declared value. When you get a payment notice, first check that it is an official notice from the carrier, then ask the user to decide.

**After delivery**

- Photograph the outer box and count quantities: number of PCBs, number of PCBAs, and whether any pin headers or parts were included.
- Solder OSP boards soon after unsealing; the shelf life unopened is about 3 months (JLC surface finish notes).
- Do a visual and short-circuit check before powering up. For the example board's full procedure, see the [bench test procedure](../../examples/max-m10s-breakout-revc-tests/README.md).
