from resources.program_types import A, L, Program

TRACK = Program(
    slug='stimulants-14-days',
    title='Quitting Stimulants: 14 Days',
    icon='⚡',
    summary='A two-week, day-by-day guide to getting through the crash, handling cue-driven cravings and rebuilding energy and enjoyment without cocaine, meth or misused stimulants.',
    intro=(
        "These fourteen short lessons walk you through the first two weeks off cocaine, crack, "
        "methamphetamine or misused prescription stimulants: the crash, the flat days, sudden "
        "cravings, sleep, food and slowly finding enjoyment again. Safety first: the low mood of "
        "the crash can be severe, so if you have any thoughts of harming yourself, call or text 988 "
        "right away, and call 911 for chest pain, a very high body temperature, seizures or "
        "confusion. Any street supply may be contaminated with fentanyl, so keep naloxone around, "
        "never use alone, and talk to a doctor about how stimulants have affected your health."
    ),
    audience='Anyone stopping cocaine, crack, methamphetamine or misused prescription stimulants who wants a steady, practical guide through the first two weeks.',
    meta_description='Free 14-day program to quit cocaine, meth and stimulants: first 3 days free. Daily lessons on the crash, cravings, sleep and feeling good again.',
    weeks=(
        'Week 1: Getting through the crash',
        'Week 2: Rebuilding energy and enjoyment',
    ),
    free_days=3,
    kind='track',
    substance='Stimulants',
    helplines=(
        ('SAMHSA National Helpline (free, 24/7)', '1-800-662-4357'),
        ('988 Suicide & Crisis Lifeline', '988'),
    ),
    lessons=(
        L('Starting safely', [
            "Deciding to stop is a big step, and the first thing to get right is safety. After a "
            "run of stimulant use, many people hit a crash: deep exhaustion, long sleep, low mood "
            "and irritability. The low can be heavier than you expect. If you have any thoughts of "
            "harming yourself, call or text 988 right away. You don't have to wait until it feels "
            "like an emergency.",
            "Some things are always emergencies. Chest pain, a very high body temperature, a seizure "
            "or confusion mean call 911 now. It's also worth talking to a doctor soon about your "
            "heart, sleep, weight and anything else you've noticed, so you know where your health "
            "stands. If you're unsure where to start, the SAMHSA National Helpline is free and open "
            "around the clock.",
            "If you do use again, any street supply may contain fentanyl. Keep naloxone nearby, "
            "never use alone, and tell someone where you are. Staying alive matters more than any "
            "streak. Today, find out where help lives in your area so it's ready before you need it.",
        ], A('Find professional help', 'resources:professional_help',
             detail='Look up a doctor, clinic or treatment option near you and save the details.'),
            "Who is one person you could call if the crash gets too heavy?"),
        L('Riding out the crash', [
            "The first days after stopping often feel like your body is collecting a debt. You may "
            "sleep far more than usual, wake up heavy, feel hungry all the time, and snap at people "
            "you love. This is the crash, and it's a normal part of stopping, not a sign that "
            "something is wrong with you.",
            "Treat these days like recovering from an illness. Sleep when you can, eat simple food, "
            "drink water, and cancel what you can cancel. Low mood is common, but if it turns into "
            "thoughts of harming yourself, call or text 988 straight away. Chest pain, overheating, "
            "seizures or confusion mean call 911.",
            "A quick daily check-in helps you see the crash as a passing stage rather than your "
            "new normal. Over a week or two, you'll likely notice the numbers shift, even if it "
            "doesn't feel that way yet. If anything worries you physically, talk to a doctor.",
        ], A('Do today\'s check-in', 'accounts:daily_checkin',
             detail='Rate your mood, cravings and energy. It takes under a minute.'),
            "What is one kind thing you can do for your body today?"),
        L('Your reason, and staying safe', [
            "On flat or heavy days, willpower runs thin. A clear reason lasts longer. Yours might be "
            "a person, your money, your heart, your job, or simply being tired of the comedown. It "
            "doesn't need to sound impressive. It needs to be true for you.",
            "Alongside your reason, keep a safety net in place. If the low mood brings thoughts of "
            "harming yourself, call or text 988. If someone has chest pain, a seizure, overheats or "
            "becomes confused, call 911. Because street supply can contain fentanyl, keep naloxone "
            "around and never use alone. Talk to a doctor about any health worries.",
            "Write your reason somewhere you'll see it every morning. The daily pledge on your home "
            "screen can hold your reason and a photo, so you start each day reminded of why. On the "
            "mornings after a bad night, that reminder can be the thing that keeps you steady until "
            "lunchtime.",
        ], A('Take today\'s pledge', 'accounts:progress',
             detail='Tap "I pledge to stay sober today" and add your reason.'),
            "If you could only keep one reason, which would it be?"),
        L('Know your cues', [
            "Stimulant cravings are often switched on by cues: cash in your pocket, payday, a "
            "certain contact in your phone, a street, a song, a Friday night. The pull can appear "
            "out of nowhere and feel enormous. That's not weakness. Your brain learned these links "
            "and is replaying them.",
            "You can't avoid every cue, but you can stop being ambushed by them. Once you know "
            "which ones are loudest, you can plan around them: who holds the cash, which route you "
            "take home, which numbers you delete.",
            "Today, map yours. It takes about fifteen minutes, and you'll use what you learn for "
            "the rest of this program. Be specific: not just \"money\" but \"Friday afternoon with "
            "cash in my pocket\". The more precise the cue, the easier it is to plan around.",
        ], A('Fill in the Trigger Map', 'resources:worksheet_detail', ('trigger-map',),
             detail='List the people, places, times, money moments and music that pull you back.'),
            "Which cue surprised you most when you wrote it down?"),
        L('When a craving hits', [
            "A stimulant craving can arrive fast and feel urgent, with a racing heart and your mind "
            "already making plans. It feels like it will keep building until you give in. It won't. "
            "Cravings rise, peak and fall, even the strong ones.",
            "Your job is to get through the peak without acting on it. Breathe slowly, leave the "
            "room, walk around the block, eat something, text someone, splash cold water on your "
            "face. Anything that buys you a few minutes is a win.",
            "Know where to go before you need it. Try the Craving SOS tools once now, while things "
            "are calm, so they feel familiar when a wave comes. Practicing in a quiet moment makes "
            "it far more likely you'll actually reach for them in a loud one.",
        ], A('Open Craving SOS', 'core:craving_sos',
             detail='Try the breathing exercise or urge surfing once now, while things are calm.'),
            "What has helped you get through a craving before, even a little?"),
        L('Money, payday and binges', [
            "For many people, stimulant use runs in binges: nothing for days, then a run that eats "
            "through the night and the bank account. Payday, a cash windfall or a free weekend can "
            "be the starting gun.",
            "Make money harder to reach on purpose. You might ask someone you trust to help manage "
            "cash for a while, set lower card limits, move savings out of easy reach, or plan "
            "something specific for the evening your pay lands. A little friction gives your better "
            "judgment time to catch up.",
            "Tracking urges also shows you the pattern. When you log each one, you start to see "
            "which days, times and situations carry the most risk. After a week or so, you'll "
            "have a clearer picture of when to put extra support in place.",
        ], A('Start an Urge Log', 'resources:worksheet_detail', ('urge-log',),
             detail='Note when each urge came, how strong it was and what you did.'),
            "What would make your next payday feel safer?"),
        L('A plan for hard moments', [
            "Most returns to use happen in moments that felt fine an hour earlier: a call from an "
            "old contact, a night out, an argument, a sudden bit of money. Deciding what to do in "
            "the moment is hard. Deciding ahead of time is much easier.",
            "A relapse prevention plan is simply your answers written down in advance: your warning "
            "signs, the people you'll contact, the things you'll do instead, and the reasons you're "
            "doing this. Keep it short and honest.",
            "If a slip does happen, treat it as information, not failure. Reach out quickly, stay "
            "safe, and look at what led up to it. Never use alone, keep naloxone nearby, and add "
            "what you learn to your plan so it gets stronger each time.",
        ], A('Build your relapse plan', 'accounts:relapse_plan',
             detail='Fill in your warning signs, contacts and go-to actions.'),
            "What is the earliest warning sign that you're heading toward a risky night?"),
        L('Sleep and eating rhythms', [
            "Stimulants push sleep and appetite around. During use you may barely sleep or eat; "
            "afterwards you may do little else. Getting back into a steady rhythm is one of the "
            "most useful things you can do this week.",
            "Aim for roughly the same wake-up time each day, even after a rough night. Get some "
            "daylight early. Eat regular meals, even small ones, rather than waiting until you're "
            "starving. Keep evenings dim and screens down before bed. None of this is dramatic, but "
            "it adds up.",
            "A short review at the end of each day helps you notice what's working and wind down "
            "on purpose. It also gives racing thoughts somewhere to land, so they're less likely "
            "to keep you awake. If sleep stays badly off, talk to a doctor.",
        ], A('Try the Nightly Review', 'resources:worksheet_detail', ('nightly-review',),
             detail='Spend five minutes looking back on today before bed.'),
            "What is one small change that would help your sleep tonight?"),
        L('When everything feels flat', [
            "A lot of people are caught off guard by the flatness. Food tastes dull, music doesn't "
            "land, and things you used to enjoy feel like effort. It can make you wonder if you'll "
            "ever feel good again without using.",
            "This flatness is common after stopping stimulants, and for most people it gradually "
            "lifts over weeks to months as the brain rebalances. It's a stage, not a permanent "
            "state. If the low mood is heavy or comes with thoughts of harming yourself, call or "
            "text 988 and talk to a doctor.",
            "Talking it through can help you find small things that still give a flicker of "
            "interest. Anchor, the AI coach, is available any time to think it over with you, "
            "including late at night when the flatness tends to feel heaviest and other people "
            "are asleep.",
        ], A('Talk it through with Anchor', 'accounts:recovery_coach',
             detail='Tell Anchor what feels flat right now and ask for small ideas to try.'),
            "What used to give you even a small spark, before stimulants took over?"),
        L('Moving your body', [
            "Exercise is one of the most reliable ways to bring back some natural energy and lift "
            "your mood. It doesn't need to be intense. A brisk walk, a bike ride, stretching or "
            "dancing in the kitchen all count.",
            "Start smaller than you think you should. Ten minutes is plenty while your body is "
            "recovering. If you've had chest pain, heart concerns or big weight changes, talk to a "
            "doctor before pushing hard. The goal is to feel a little better afterwards, not to "
            "punish yourself.",
            "Movement also works as a craving tool: when a wave hits, getting up and walking often "
            "takes the edge off. Try noting in your check-in whether you moved today, and watch "
            "how it lines up with your mood and energy over the week.",
        ], A('Do today\'s check-in', 'accounts:daily_checkin',
             detail='Log your mood and energy, and note whether you moved today.'),
            "What kind of movement could you actually see yourself enjoying?"),
        L('Settling anxiety and suspicion', [
            "Stimulant use can leave you jumpy, on edge or suspicious of people, sometimes even "
            "after you stop. You might read threats into ordinary looks or feel unsafe without a "
            "clear reason. For most people this settles with sleep, food and time away from use.",
            "In the meantime, slow your body down: long breaths out, feet on the floor, naming "
            "things you can see and hear. Check worrying thoughts with someone you trust before "
            "acting on them. If fear or confusion becomes intense, talk to a doctor, and call 911 "
            "in an emergency.",
            "Grounding exercises are worth practicing now, so they come easily when you need them. "
            "A few minutes a day is enough. Over time, your body learns that it can calm down "
            "without anything outside itself, which is a skill you'll keep.",
        ], A('Practice grounding', 'core:craving_sos',
             detail='Try the grounding exercise and notice how your body feels afterwards.'),
            "What helps you feel safe when your mind starts racing?"),
        L('Small rewards, real enjoyment', [
            "Stimulants offered a fast, huge reward. Ordinary life can seem quiet next to that. The "
            "way back to enjoyment is through many small, real rewards that add up, rather than "
            "waiting for one big feeling.",
            "Plan a few on purpose this week: a good meal, a film, time outdoors, a call with a "
            "friend, putting saved money toward something you want. Notice them, even if they feel "
            "muted at first. Your capacity for pleasure grows with practice.",
            "It helps to remember what you actually care about. Values give your days direction "
            "when the old excitement is gone. Knowing what matters to you, such as family, health, "
            "creativity or honesty, makes small rewards feel like steps toward something.",
        ], A('Fill in the Values Compass', 'resources:worksheet_detail', ('values-compass',),
             detail='Pick the values that matter most and one small step toward each.'),
            "What small reward could you plan for yourself this week?"),
        L('Connection over isolation', [
            "Stimulant use often comes with a particular social world: certain people, certain "
            "nights, certain places. Stepping away can leave a gap, and loneliness is a risky "
            "feeling in early recovery, especially on the nights you used to go out.",
            "Filling that gap with people who support where you're going makes a real difference. "
            "That might be a meeting, a group, an old friend you drifted from, or other people here "
            "who are working on the same thing. You don't have to share everything at once. "
            "Showing up is enough to start.",
            "Today, try one meeting, in person or online, of whatever kind suits you. There are "
            "12-step, SMART, secular and faith-based options. You can simply listen the first time. "
            "Notice how it feels to be in a room with people who understand.",
        ], A('Find a meeting', 'support_services:meeting_list',
             detail='Browse 12-step, SMART and other meetings, online or near you.'),
            "Who in your life makes you feel more like yourself?"),
        L('Two weeks, and what comes next', [
            "Two weeks ago you decided to stop. Since then you've faced the crash, learned your cues, "
            "worked through cravings and flat days, and started rebuilding sleep, food, movement and "
            "connection. That's real work, whether it went perfectly or not.",
            "Recovery from stimulants keeps getting easier for most people as energy and enjoyment "
            "slowly return over the coming weeks and months. Keep using what helps: your check-ins, "
            "your relapse plan, Craving SOS, meetings and the people in your corner. The First 30 "
            "Days program is a good next step.",
            "Mark this point. Recording a milestone gives you something to look back on when a hard "
            "day comes. Then keep going: join a group, keep checking in, and let the community here "
            "see your progress. Two weeks is the foundation, not the finish line.",
        ], A('Add a milestone', 'accounts:add_milestone',
             detail='Record your two weeks and add a note about what helped most.'),
            "What do you want to remember about these two weeks when the next hard day comes?"),
    ),
)
