from resources.program_types import A, L, Program

TRACK = Program(
    slug='family-and-friends',
    title='Supporting Someone You Love: 14 Days',
    icon='🤝',
    summary='A two-week, day-by-day guide for parents, partners, adult children, siblings and friends of someone struggling with alcohol, drugs or gambling.',
    intro=(
        "Loving someone with an addiction can leave you exhausted, frightened and unsure what "
        "to do next. These fourteen short lessons are for you, not for them: how to look after "
        "yourself, talk in a way that can be heard, set boundaries you can keep, stay safe, and "
        "encourage help without forcing it. Whether or not the person you love is ready to "
        "change, you deserve support too."
    ),
    audience='Family members and friends of someone with an alcohol, drug or gambling problem, whether or not that person is in recovery yet.',
    meta_description='How to help a loved one with addiction: a 14-day guide for family and friends on self-care, talking, boundaries and safety. First 3 days free.',
    weeks=(
        'Week 1: Taking care of you, and talking differently',
        'Week 2: Boundaries, help and the road ahead',
    ),
    free_days=3,
    kind='family',
    substance='Family & friends',
    access='family',
    helplines=(
        ('SAMHSA National Helpline (free, 24/7)', '1-800-662-4357'),
        ('National Domestic Violence Hotline', '1-800-799-7233'),
        ('988 Suicide & Crisis Lifeline', '988'),
    ),
    lessons=(
        L("You are not alone, and it's not your fault", [
            "If you are here, someone you love is struggling with alcohol, drugs or gambling, and "
            "you have probably been carrying a lot on your own. Maybe you've lain awake wondering "
            "where they are, or replayed old conversations looking for what you did wrong. Many "
            "people in your position feel exactly this, even if nobody around you talks about it.",
            "Here is something worth hearing clearly: you did not cause their addiction, and you "
            "cannot control it or make it stop. No perfect sentence, rule or sacrifice will do that "
            "on its own. Letting go of that impossible job is not giving up on them. It is putting "
            "down a weight that was never yours to carry alone.",
            "What you can do is real, though. The way you respond, talk and look after yourself "
            "can shape the atmosphere around them and make change feel more possible. Over these "
            "two weeks you'll work on those things, one small step a day, starting with you. Short "
            "daily readings can be a gentle way to begin each morning.",
        ], A('Read a daily reflection', 'resources:reflections',
             detail="Read today's short reflection and notice one line that speaks to you."),
            "What have you been blaming yourself for that you could start to set down?"),
        L('Your own wellbeing comes first', [
            "When someone you love is in trouble, your own needs tend to slide quietly off the "
            "list. Meals get skipped, sleep gets broken, friendships fade, and the things that used "
            "to bring you joy start to feel selfish. Over time, that leaves you running on empty, "
            "and it becomes harder to think clearly or respond calmly.",
            "Looking after yourself is not abandoning them. Think about the basics first: a "
            "regular bedtime, real food, a little movement, and at least one person you can be "
            "honest with. Then add something that refills you, whether that's a walk, music, a "
            "hobby, prayer or an hour with a friend who makes you laugh.",
            "Writing helps too. A private journal gives your worries somewhere to land so they "
            "don't circle all night. Nobody else will read it. Try a few lines tonight about how "
            "you are really doing, not how they are doing. It may be the first time in a while "
            "you've asked yourself that question.",
        ], A('Start your private journal', 'journal:create_entry',
             detail='Write a few honest lines about how you are doing, just for you.'),
            "What is one small thing that used to refill you that you could make room for this week?"),
        L('Safety first', [
            "Your physical safety, and the safety of any children in your care, comes before "
            "everything else in this program. If you are ever in danger, leave and call 911. If "
            "you are being threatened, hurt or controlled, the National Domestic Violence Hotline "
            "at 1-800-799-7233 can help you make a safety plan, confidentially, any time of day.",
            "If the person you love uses opioids or street drugs, learn the signs of an overdose: "
            "they can't be woken, their breathing is very slow or has stopped, or their lips or "
            "fingertips look blue or gray. Call 911 right away. Naloxone, often sold as Narcan, "
            "can reverse an opioid overdose, and a pharmacist can tell you how to get it.",
            "Keep naloxone where you can find it fast, and stay with them until help arrives. If "
            "you or they ever feel like giving up on life, call or text 988. The crisis page "
            "keeps every emergency number in one place, so you won't have to search when every "
            "second counts.",
        ], A('Open crisis resources', 'core:crisis',
             detail='Save the crisis page and note which numbers matter most for your situation.'),
            "If something went wrong tonight, where would you go and who would you call?"),
        L("Understanding what they're going through", [
            "From the outside, it can be baffling. They say they want to stop, then they don't. "
            "They seem sorry one day and defensive the next. Most people caught in addiction feel "
            "deeply mixed about change. Part of them wants out, and part of them is afraid of "
            "life without the thing that has been helping them cope.",
            "Addiction changes how the brain weighs rewards and stress, which can make stopping "
            "far harder than it looks. Many people are also carrying pain underneath, such as "
            "anxiety, grief, trauma or loneliness. Seeing this can soften some of your anger and "
            "help you respond to the person, not just the behavior.",
            "Understanding is not the same as excusing. Their struggle does not make lies, "
            "cruelty or danger acceptable, and you are allowed to be hurt and angry. Holding both "
            "at once, compassion for them and honesty about the harm, is hard. It is also one of "
            "the most useful things you can learn to do.",
        ], None,
            "When you picture the person you love at their best, what do you see?"),
        L('Talking in a way that can be heard', [
            "When you're scared, it's natural to lecture, plead or argue. The trouble is that "
            "most people get defensive when they feel attacked, and then nothing gets through. "
            "Small changes in how you talk can make a surprising difference to whether they can "
            "actually hear you, and to how you feel afterward.",
            "Pick a calm moment, never when they are drunk, high, hungover or in the middle of a "
            "bet. Keep it short. Be specific about one thing you saw, and speak from your side: "
            "\"I felt scared when you didn't come home last night\" lands differently from \"You "
            "always do this.\" Let them know you care before you say what worries you.",
            "Then listen. Ask a question and give them room to answer without jumping in to "
            "correct them. You don't have to agree with everything to show you've heard it. "
            "Conversations that end with both people a little calmer are worth more than ones "
            "where you say everything but nobody feels understood.",
        ], None,
            "What is one phrase you often use when you're upset that you'd like to say differently?"),
        L('Planning one hard conversation', [
            "Some conversations are too important to leave to chance. If there's something you "
            "need to say, whether about what you've noticed, how it affects you or a change you're "
            "making, planning it ahead makes it far more likely to go the way you hope. It also "
            "helps you stay steady if they react badly.",
            "Think about timing, place and what you want them to hear in one or two sentences. "
            "Decide what you'll say if they get angry, deny it or walk away. It's fine to end the "
            "conversation early and try again another day. Your goal is not to win or to get a "
            "promise. It's to be honest and leave the door open.",
            "If you have reason to think the conversation could make them violent, don't have it "
            "alone, and put your safety first. Otherwise, the conversation planner walks you "
            "through each step, from your opening line to how you'll look after yourself "
            "afterward. Work on it slowly, and share it with someone you trust if that helps.",
        ], A('Use the conversation planner', 'resources:worksheet_detail', ('conversation-planner',),
             detail='Plan one conversation: when, where, your opening words and what you will do if it goes badly.'),
            "What do you most want them to understand, in one sentence?"),
        L('Noticing and encouraging the good', [
            "When you've been hurt over and over, it's easy to notice only the bad days. But "
            "people are more likely to repeat what feels good and is recognized. Warmly noticing "
            "the times they are sober, honest or making an effort can quietly make those times "
            "more appealing than the alternative.",
            "Keep it simple and genuine. \"It was really good to have dinner with you tonight.\" "
            "\"Thank you for telling me the truth about that.\" You don't need to make a big "
            "speech or mention the addiction at all. A smile, a thank you or an offer to do "
            "something together can say a great deal.",
            "Try to spend time with them when they're not using, doing things you both enjoy, "
            "like a walk, a meal, a game or a drive. Those moments remind both of you what life "
            "can feel like. Being clear about what matters most to you can help you see which "
            "moments are worth leaning into.",
        ], A('Try the Values Compass', 'resources:worksheet_detail', ('values-compass',),
             detail='Name what matters most to you in this relationship and in your own life.'),
            "When was the last time you enjoyed being with them, and what were you doing?"),
        L('Stepping back from rescuing', [
            "When you love someone, cleaning up after them can feel like the only kind thing to "
            "do. You call in sick for them, cover the bills, explain away missed events or tidy "
            "up before anyone sees. It comes from love. But it can also mean they never fully "
            "feel the effects of what is happening.",
            "There's a difference between helping and shielding. Helping supports their health "
            "and growth, like a lift to an appointment or a meal together. Shielding protects the "
            "addiction from its consequences. People sometimes call this enabling, but it isn't a "
            "character flaw. It's what caring people do when they're frightened and want the pain "
            "to stop.",
            "Stepping back means letting natural consequences happen when it's safe to, such as "
            "a missed shift, a phone bill they must pay or an awkward explanation they have to "
            "give. It may feel harsh at first. Notice tonight where you've been rescuing, and "
            "write about one thing you could gently stop doing.",
        ], A('Reflect in your journal', 'journal:create_entry',
             detail='List the ways you have been covering for them, and circle one you could stop.'),
            "What is one thing you do for them that they could reasonably do for themselves?"),
        L('Your boundaries', [
            "A boundary is not a rule for someone else. It's a decision about what you will and "
            "won't do. \"I won't lend money anymore.\" \"I'll leave the room if you're shouting.\" "
            "\"I won't let you drive the kids after you've been drinking.\" Boundaries protect "
            "your wellbeing, your home and anyone who depends on you.",
            "Start small and choose boundaries you can actually keep. Say them calmly, at a quiet "
            "time, without threats or anger. Then follow through, even when it's uncomfortable. "
            "A boundary that keeps shifting teaches everyone that it doesn't really count, while "
            "one held kindly and firmly builds trust over time.",
            "Expect pushback. People often test a new boundary to see if it's real, and you may "
            "feel guilty holding it. That doesn't mean you're doing it wrong. The boundaries "
            "worksheet helps you write down each boundary and exactly what you'll do if it's "
            "crossed, so you're not deciding in the heat of the moment.",
        ], A('Write your boundaries plan', 'resources:worksheet_detail', ('boundaries-plan',),
             detail='List two or three boundaries and what you will do if each one is crossed.'),
            "Which boundary would make the biggest difference to your peace of mind right now?"),
        L('Encouraging help', [
            "You can't make someone get help, but you can make it easier for them to say yes. "
            "People are often most open just after something painful, like a bad night, a scare "
            "or a moment of regret. Those quiet, honest moments are when a gentle offer has the "
            "best chance of being heard.",
            "Have something specific ready rather than a general \"you need help.\" Maybe a "
            "doctor's appointment you'd go to with them, a counselor's name, a meeting time, or "
            "the SAMHSA National Helpline at 1-800-662-4357, which is free and open around the "
            "clock. Offer, don't demand, and if they say no, let it rest and try again later.",
            "Do the groundwork now, while things are calm. Look up treatment programs, "
            "therapists and family counselors in your area so you're ready when the moment comes. "
            "A family therapist can also help you, whether or not they decide to go. Getting "
            "support for yourself is never wasted.",
        ], A('Find treatment and counselors', 'resources:professional_help',
             detail='Look up treatment programs, therapists or family counselors and save one or two.'),
            "If they said \"okay, I'll get help\" tomorrow, what would you want to have ready?"),
        L("When they're in recovery", [
            "If the person you love has started recovery, you may feel relief, hope and a fair "
            "amount of fear all at once. It's normal to want to watch every move. But checking "
            "their phone, counting drinks or asking constantly how they're doing can feel like "
            "policing, and it can add pressure at an already fragile time.",
            "Instead, ask what kind of support they'd find helpful, and respect the answer. Notice "
            "and celebrate milestones, whether a week, a month or a year, in whatever way feels "
            "right to them. Keep building your own life too. Their recovery belongs to them, and "
            "yours deserves attention as well.",
            "If they're open to it, you can invite them to MyRecoveryPal and become a supporter "
            "in their Support Circle. With their consent, you'll see the progress they choose to "
            "share and can send encouragement on the hard days. It's an easy way to show you're "
            "in their corner without hovering.",
        ], A('Invite them to MyRecoveryPal', 'accounts:supporter_invite_member',
             detail='Send an invite, and let them decide what they want to share with you.'),
            "What kind of support would you have wanted if you were in their shoes?"),
        L('If they slip or relapse', [
            "Relapse can feel crushing, especially after a stretch of hope. You may feel angry, "
            "betrayed or foolish for believing things had changed. Those feelings are valid. It "
            "may help to know that slips are a common part of many people's recovery and don't "
            "erase the progress that came before.",
            "When you talk about it, try to do so without shame or blame. Something like \"I'm "
            "worried, and I'm still here\" leaves room for them to come back toward help. Keep "
            "the boundaries you've set. Supporting someone through a slip doesn't mean going back "
            "to rescuing or covering for them.",
            "Look after yourself first. Return to the basics that steady you, and lean on the "
            "people who support you. Remember the safety steps from earlier: if they use opioids "
            "or street drugs, keep naloxone close and call 911 for any sign of overdose. A short "
            "review at night can help you notice how you're coping.",
        ], A('Try the nightly review', 'resources:worksheet_detail', ('nightly-review',),
             detail='At the end of today, note what was hard, what helped and one kind thing you did for yourself.'),
            "How do you want to respond if they tell you they've slipped?"),
        L('Your own support', [
            "You've spent a long time holding things together for someone else. You deserve "
            "people who hold you too. Talking with others who understand, people who've also "
            "loved someone through addiction, can ease the loneliness in a way that even close "
            "friends sometimes can't.",
            "Family support groups meet in person and online, including Al-Anon, Nar-Anon and "
            "SMART Recovery Family & Friends. Each has its own style, so try a few and see where "
            "you feel at home. You can also look for a counselor who works with families, or "
            "join a family group here in the community.",
            "Don't forget the trusted people already in your life. You don't need to share every "
            "detail. A friend who will listen for half an hour, or simply take you out for "
            "coffee, can matter more than you'd expect. Reaching out is not burdening them. It's "
            "giving them a chance to care for you.",
        ], A('Find a family support meeting', 'support_services:meeting_list',
             detail='Search for a family support meeting, online or near you, and pick one to try.'),
            "Who is one person you could be more honest with about how things really are?"),
        L('The long view', [
            "Change in addiction rarely moves in a straight line. There may be good months and "
            "hard ones, progress and setbacks. Patience isn't the same as accepting everything. "
            "It means trusting that your steady, loving presence and your clear boundaries still "
            "matter, even when you can't see the results yet.",
            "Keep doing what you've practiced here. Look after your own health and friendships. "
            "Talk calmly and notice the good. Let consequences happen, and hold your boundaries. "
            "Keep your safety plan close, and keep the door to help open. Come back to these "
            "lessons whenever you need a reminder.",
            "Most of all, remember that you matter regardless of the choices they make. Your "
            "life, your peace and your hope are worth protecting. Connecting with other families "
            "who understand can keep you going on the long road, so you don't have to walk it "
            "alone.",
        ], A('Join a community group', 'accounts:groups_list',
             detail='Find a group for family and friends and introduce yourself when you are ready.'),
            "What do you want to keep doing for yourself, no matter what happens next?"),
    ),
)
