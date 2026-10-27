# pcb-agent-workflow

A workflow for "people plus agents designing PCBs and having JLCPCB manufacture them". This file holds only the terms this workflow defines itself, so agents use consistent wording; general PCB terms are in [docs/glossary.md](docs/glossary.md).

## Versions

**Release package**:
The design and manufacturing files of the version sent to the factory. Once handed over, its contents are not modified; fixes go into a new version.
_Avoid_: official version, final version, release (on its own)

**Working copy**:
A design copy that may be modified. Commands that write files, such as anything with `--save-board`, run only here.
_Avoid_: test version

**Candidate version**:
A version being modified and not yet settled; it may become the next release package or be discarded.
_Avoid_: new version, latest version

**Verification**:
Checks run on the files before release (ERC, DRC, diff checks, agent review); the results are frozen together with the release package.
_Avoid_: testing (easily confused with bench testing)

**Bench test record**:
Power-on and functional test results after real boards arrive, plus any errata found as a result. Kept outside the release package and keeps growing.
_Avoid_: verification, test report (the kind put in a release package)

## Confirmation after payment

**Confirmation items**:
Umbrella term for what the factory asks the customer to confirm after payment, including the production file and parts placement confirmation.
_Avoid_: DFM (DFM is the factory's review, not something you are asked to confirm)

**Production file**:
Refers only to the PCB CAM file (Confirm Production file), processed by the factory and possibly with rails added.
_Avoid_: using "production file" to mean PCBA confirmation in general

**Parts placement confirmation**:
Refers only to confirming PCBA component position, rotation, and polarity (Confirm Parts Placement); if overdue, it goes into production automatically.
_Avoid_: placement file, placement draft

## Communicating with the factory

**Status chase**:
A message asking about progress and requesting a responsible person and the next update time; it contains no agreement or choice of any kind.
_Avoid_: follow-up (too vague)

**Pure technical clarification**:
A message that only asks for the reason, requests images, or asks what a reading means; it contains no agreement, choice, or modification request. Replying "we agree to the factory's changes" is not a pure technical clarification.
_Avoid_: technical reply, engineering confirmation

**Accepting factory changes**:
Agreeing to CAM changes, extra fees, compensation, or rescheduling proposed by the factory. Requires the user's explicit consent every time.
_Avoid_: confirm (confused with confirmation items)

**Boundary statement**:
The sentence at the end of every outgoing message stating "this does not approve any change or fee; please keep manual confirmation".
_Avoid_: disclaimer
