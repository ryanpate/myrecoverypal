from resources.program_types import A, L, Program

TRACK = Program(
    slug='opioids-14-days',
    title='Recovering from Opioids: 14 Days',
    icon='🌤️',
    summary='A two-week, day-by-day guide to stepping away from prescription painkillers, heroin or fentanyl, staying safe, and finding the treatment and people that make recovery last.',
    intro=(
        "These fourteen short lessons walk you through the first two weeks of recovery from "
        "opioids, whether that's prescription painkillers, heroin or fentanyl. Safety comes first: "
        "after any break, your tolerance drops, so a return to use carries a much higher risk of "
        "fatal overdose, and fentanyl makes any street supply unpredictable. Keep naloxone (Narcan) "
        "on hand, never use alone, and call 911 in an overdose. Talking to a doctor or treatment "
        "provider, including about medication-assisted treatment, is one of the strongest first steps."
    ),
    audience='Anyone stopping or cutting back on prescription painkillers, heroin or fentanyl, or already in treatment, who wants a steady day-by-day guide through the first two weeks.',
    meta_description='Free 14-day opioid recovery program, first 3 days free. Daily lessons on withdrawal, overdose safety, treatment options, shame and rebuilding trust.',
    weeks=(
        'Week 1: Getting through safely',
        'Week 2: Rebuilding your life and your support',
    ),
    free_days=3,
    kind='track',
    substance='Opioids',
    helplines=(
        ('SAMHSA National Helpline (free, 24/7)', '1-800-662-4357'),
        ('988 Suicide & Crisis Lifeline', '988'),
    ),
    lessons=(
        L('Starting safely', [
            "Choosing to step away from opioids takes real courage, and the first thing to get right "
            "is staying alive. After even a short break, your tolerance drops. An amount your body "
            "once handled can now stop your breathing. That's why a return to use after stopping is "
            "one of the most dangerous moments there is, and why safety comes before everything else.",
            "Street supply is unpredictable because fentanyl turns up in pills and powders that look "
            "like something else. Get naloxone (Narcan), which reverses opioid overdoses, and tell the "
            "people around you where it is. Many pharmacies provide it without a prescription. If you "
            "ever do use, never use alone, and in any overdose call 911.",
            "None of this means you expect to fail. It means you're protecting the person doing the "
            "hard work of recovery. A slip is not the end of anything, but you have to be alive to "
            "learn from it. If you don't know where to start, the SAMHSA National Helpline is free "
            "and open around the clock.",
        ], A('Find treatment and support near you', 'resources:professional_help',
             detail='Look up a doctor or treatment provider you could call this week.'),
            "Who in your life could you tell where your naloxone is kept?"),
        L('Withdrawal is hard, and it passes', [
            "Opioid withdrawal can feel miserable: aches, sweats, restlessness, stomach trouble, poor "
            "sleep and a heavy, low mood. It's one of the main reasons people go back to using. "
            "Knowing it's coming, and that it does pass, takes away some of its power. You are not "
            "weak for finding it hard. It is hard.",
            "You don't have to white-knuckle it alone. A doctor or treatment provider can help you "
            "through withdrawal more safely and comfortably, and can talk with you about medication. "
            "Rest, fluids, simple food, warm showers and someone checking in on you all help. Ask a "
            "doctor or pharmacist before taking anything for symptoms.",
            "Remember the safety point from yesterday, because it matters most right now. Using to "
            "stop withdrawal after days without opioids is when overdose risk is highest. Keep "
            "naloxone close, make sure someone knows where it is, never use alone, and call 911 if "
            "someone won't wake up or is barely breathing.",
        ], A('Do today\'s check-in', 'accounts:daily_checkin',
             detail='Rate your mood and cravings so you can watch the hardest days ease.'),
            "What is one small comfort you can line up for yourself on the roughest day this week?"),
        L('Medication-assisted treatment is real recovery', [
            "You may have heard that using medication to treat opioid addiction is cheating, or just "
            "trading one drug for another. It isn't. Medication-assisted treatment is a legitimate, "
            "evidence-based path, prescribed and monitored by professionals, that helps many people "
            "stabilize, stay alive and rebuild their lives.",
            "Whether it's right for you is a conversation for you and a doctor or treatment provider. "
            "They can explain the options, what to expect and how it fits with counseling and "
            "support. Asking doesn't commit you to anything. It just means you're making the decision "
            "with full information instead of with other people's opinions.",
            "If anyone, including a voice in your own head, tells you this path doesn't count, you "
            "can let that go. Recovery is measured by how your life is going, not by which tools you "
            "used to get there. Every path that keeps you alive and moving forward counts.",
        ], A('Look for a treatment provider', 'resources:professional_help',
             detail='Find a doctor or program you could ask about medication-assisted treatment.'),
            "What questions would you want to ask a doctor about your treatment options?"),
        L('Why you\'re doing this', [
            "On hard days, willpower runs out. Reasons last longer. Take a moment to name yours. It "
            "might be your kids, your health, a job you want back, or simply being tired of living "
            "around the next dose. Any honest reason is a good one.",
            "Opioids often take over slowly, until the whole day is organized around getting, using "
            "and recovering. Your reason is a reminder of the life underneath all that, the one "
            "you're making room for again. It helps to see it every morning, before the day gets loud.",
            "The daily pledge on your home screen can hold your reason, and a photo if you like. "
            "Taking it each morning is a small, steady way of choosing again, one day at a time. "
            "Over time, the pledge streak becomes its own quiet reminder of how far you have come.",
        ], A('Take today\'s pledge', 'accounts:progress',
             detail='Tap the pledge card and add the reason that matters most to you.'),
            "If you could only keep one reason for recovery, which would it be?"),
        L('Know your triggers', [
            "A trigger is anything that makes you want to use: a person, a place, a feeling, a phone "
            "number, payday, physical pain, or even a time of day. Everyone in recovery has them. "
            "Noticing them isn't a weakness. It's the first step to not being caught off guard.",
            "With opioids, triggers often include the people and routes connected to getting them, "
            "and the feelings opioids used to numb, like loneliness, stress or old hurts. Writing them "
            "down helps you see the pattern instead of being pulled along by it.",
            "Today, map your triggers. It takes about fifteen minutes, and what you learn will shape "
            "the rest of this program. Be as specific as you can. \"Fridays after my shift\" is far "
            "more useful than \"stress\", because a specific trigger is one you can plan around.",
        ], A('Fill in the Trigger Map', 'resources:worksheet_detail', ('trigger-map',),
             detail='Work through people, places, feelings and times that pull you toward using.'),
            "Which trigger surprised you most when you wrote it down?"),
        L('Riding out a craving', [
            "Cravings can feel urgent, physical and endless, as if they'll only stop once you give "
            "in. They don't work that way. A craving builds, peaks and fades, even when it feels "
            "like it won't. Your job is to get through the peak without acting on it.",
            "Simple things help: slow breathing, a cold drink, a walk, a shower, changing rooms, or "
            "calling someone and saying it out loud. Urge surfing means noticing the craving like a "
            "wave, describing it to yourself, and letting it pass without obeying it.",
            "Find your tools before you need them. Open Craving SOS now, while things are calm, so "
            "it's one tap away when a wave hits. Practicing a skill on an easy day makes it much "
            "easier to reach for on a hard one, when your thinking feels foggy and rushed.",
        ], A('Open Craving SOS', 'core:craving_sos',
             detail='Try the breathing exercise once now, while you feel steady.'),
            "What has helped you get through a craving before, even a little?"),
        L('Pain without misuse', [
            "For many people, opioids started with real pain: an injury, surgery or a long-term "
            "condition. That pain doesn't disappear because you've stopped, and it's fair to be "
            "worried about it. You deserve pain care that doesn't put your recovery at risk.",
            "Be honest with your doctor about your history with opioids. It can feel exposing, but it "
            "lets them plan pain treatment that keeps you safe. There are many approaches to managing "
            "pain, and a doctor can help you find the ones that fit your body and your recovery.",
            "If you're facing a procedure or a flare-up, talk to a doctor ahead of time rather than in "
            "the middle of it. Planning early protects you from having to make a hard decision while "
            "you're hurting.",
        ], A('Find a doctor to talk to', 'resources:professional_help',
             detail='Look for a doctor you can be honest with about pain and recovery.'),
            "What would you want a doctor to understand about your pain and your recovery?"),
        L('Shame and isolation', [
            "Opioid use often comes wrapped in secrecy, and secrecy feeds shame. You may feel like "
            "you've done things you can't talk about, or that people would see you differently if "
            "they knew. That feeling is common in recovery, and it is not the whole truth about you.",
            "Shame pushes you to hide, and hiding cuts you off from the very people who could help. "
            "Isolation is one of the riskiest places to be in early recovery, emotionally and "
            "physically. Connection, even small amounts of it, is part of staying safe.",
            "You don't have to share everything. You only have to let someone in a little. A short "
            "post in the community, read by people who understand, can be a gentle place to start. "
            "You can keep it simple and say only as much as feels safe today.",
        ], A('Say hello in the community', 'accounts:social_feed',
             detail='Share one honest line about how your first week has gone.'),
            "What is one thing you've been carrying alone that you might be ready to share with someone?"),
        L('Finding your people', [
            "Recovery is easier with people who get it. Some find that in 12-step meetings, others in "
            "SMART Recovery, secular groups, faith communities or treatment programs. There's no "
            "single right room. The right one is the one you'll keep showing up to.",
            "Meetings happen in person and online, at all hours, which matters when nights are long "
            "and sleep is patchy. You can sit and listen without saying a word. Hearing someone "
            "describe your exact struggle can loosen the grip of shame in a way nothing else does.",
            "Try one meeting this week. If it doesn't feel right, try a different kind. Give a few "
            "a chance before you decide. Arriving a little early or staying a few minutes after is "
            "often where the real conversations, and the phone numbers, get shared.",
        ], A('Find a meeting', 'support_services:meeting_list',
             detail='Pick one meeting, online or nearby, to try in the next few days.'),
            "What would make it easier for you to walk into, or log into, your first meeting?"),
        L('Rebuilding trust', [
            "If opioids have strained your relationships, you may be facing hurt, suspicion or "
            "distance from the people you love. That's painful, and it's understandable. Trust was "
            "lost over time, and it comes back the same way, slowly, through what you do day after day.",
            "You can't talk anyone into trusting you again, and you don't need to. Keep small "
            "promises. Be where you said you'd be. Be honest, especially when it's uncomfortable. "
            "Let people have their feelings without arguing them out of it.",
            "Inviting someone in as a supporter can help. It gives them a way to see your progress "
            "and cheer you on, on your terms, without needing to check up on you. Choose someone who "
            "wants good things for you, even if things between you are still tender.",
        ], A('Invite a supporter', 'accounts:supporter_invite',
             detail='Invite one person you trust to follow your progress.'),
            "Whose trust would you most like to rebuild, and what is one small promise you could keep to them this week?"),
        L('Facing the fallout', [
            "Opioid use often leaves practical wreckage: debts, unpaid bills, legal trouble, a lost "
            "job or a damaged record. Looking at it can feel overwhelming, and it's tempting to keep "
            "avoiding it. But avoidance tends to make these problems grow, and the stress can feed "
            "cravings.",
            "Try writing everything down in one list, then choose a single next step for just one "
            "item. A phone call, an appointment, opening a letter. You don't have to solve it all "
            "this week. You only have to stop running from it.",
            "Legal and money problems are often easier with help. A treatment provider, counselor or "
            "legal aid service may be able to guide you. Asking for help with this is part of "
            "recovery too. Seeing the real costs on paper can also strengthen your reasons for "
            "staying the course.",
        ], A('Weigh the costs and benefits', 'resources:worksheet_detail', ('cost-benefit-analysis',),
             detail='List what using has cost you and what recovery could give back.'),
            "What is one piece of the fallout you could take a single small step on this week?"),
        L('If you slip, safety first', [
            "A slip is not a failure and it doesn't erase your progress. But after a break, your "
            "tolerance is lower, and returning to an old amount can be fatal. Fentanyl makes any "
            "street supply unpredictable. A slip is a moment to protect your life first, then learn "
            "from it.",
            "If you're at risk of using, don't use alone. Keep naloxone (Narcan) where people can find "
            "it, and make sure they know how to use it. Many pharmacies provide it without a "
            "prescription. If someone won't respond or their breathing is slow or stopped, call 911.",
            "After any slip, reach out quickly: a friend, a supporter, a meeting, your doctor or the "
            "SAMHSA National Helpline. Then write down what happened and what you'll do differently. "
            "A written relapse plan makes all of this easier in the moment.",
        ], A('Build your relapse plan', 'accounts:relapse_plan',
             detail='Add your naloxone location, who to call, and your warning signs.'),
            "Who would you call first if you slipped, and do they know that?"),
        L('Days worth filling', [
            "When opioids leave, they leave a gap: hours that used to be spent getting, using or "
            "recovering. Empty time and boredom are risky in early recovery. Filling that time with "
            "things that matter to you is one of the most protective things you can do.",
            "Think about sleep, food, movement, work, people, rest and something that's just for "
            "you. Small, steady routines rebuild a sense of control. They don't need to be "
            "impressive. A daily walk or a regular meal with someone counts.",
            "Today, look at how your life is balanced and pick one area to give a little more "
            "attention this week. Choose something small enough that you could start it tomorrow, "
            "like a set bedtime or a short walk after lunch.",
        ], A('Use the Lifestyle Balance Wheel', 'resources:worksheet_detail', ('lifestyle-balance-wheel',),
             detail='Rate each area of your life and choose one to strengthen.'),
            "What is one routine you'd like to build into your days over the next month?"),
        L('Two weeks, and what comes next', [
            "Look back at where you started. You've learned about withdrawal, tolerance and naloxone, "
            "mapped your triggers, faced shame and fallout, and started rebuilding trust. Whatever "
            "these two weeks looked like, you kept coming back, and that's worth marking.",
            "Please keep safety close as you go on. Tolerance stays lower the longer you're away from "
            "opioids, and fentanyl keeps any supply unpredictable. Keep naloxone (Narcan) on hand, "
            "let people know where it is, never use alone, and call 911 in an overdose.",
            "Next, consider the First 30 Days program, keep going to meetings, stay in touch with "
            "your doctor or treatment provider, and lean on the community. Recovery grows through "
            "connection. Mark this milestone and let it remind you how far you've come.",
        ], A('Add your milestone', 'accounts:add_milestone',
             detail='Record your two weeks so you can look back on it later.'),
            "What do you want to carry with you from these two weeks into the next month?"),
    ),
)
