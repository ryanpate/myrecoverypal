from resources.program_types import A, L, Program

TRACK = Program(
    slug='cannabis-14-days',
    title='Quitting Cannabis: 14 Days',
    icon='🌿',
    summary='A two-week, day-by-day guide to stopping cannabis, getting through withdrawal and rebuilding sleep, evenings and friendships without it.',
    intro=(
        "These fourteen short lessons walk you through the first two weeks without cannabis: "
        "withdrawal, sleep, boredom, feelings that come back un-numbed, and the friends and shops "
        "that made it so easy. Wanting to stop is reason enough, whatever anyone else thinks. "
        "If anxiety, low mood or sleep problems feel severe or don't ease, please talk to a doctor."
    ),
    audience='Anyone who wants to stop smoking, vaping or eating cannabis, or take a serious break from it, and would like a steady guide through the first two weeks.',
    meta_description='Free 14-day quit weed program: first 3 days free. Daily lessons on cannabis withdrawal, sleep, boredom, smoking friends and staying quit.',
    weeks=(
        'Week 1: Getting through withdrawal',
        'Week 2: Building days that work without it',
    ),
    free_days=3,
    kind='track',
    substance='Cannabis',
    helplines=(
        ('SAMHSA National Helpline (free, 24/7)', '1-800-662-4357'),
        ('988 Suicide & Crisis Lifeline', '988'),
    ),
    lessons=(
        L('Yes, this counts', [
            "A lot of people who want to stop cannabis hear the same thing, sometimes from their "
            "own head: it's only weed, it's not a real problem. But if it's taking more of your "
            "time, money, energy or peace than you want it to, that is reason enough. You don't "
            "need anyone's permission to decide it's time.",
            "Quitting cannabis is a real change, and it can be harder than people expect. That "
            "isn't a sign that something is wrong with you. Habits that run through your mornings, "
            "evenings and sleep take some unpicking, and you're allowed to take that seriously.",
            "Start by writing down why you want to stop. Keep it honest and in your own words, even "
            "if it feels small. On hard days, a clear reason lasts longer than willpower. The daily "
            "pledge on your home screen can show that reason, and a photo if you like, every morning.",
        ], A('Take today\'s pledge', 'accounts:progress',
             detail='Tap the pledge button and add your reason for stopping.'),
            "What finally made you decide that now is the time to stop?"),
        L('What withdrawal can feel like', [
            "Cannabis withdrawal is real. In the first days and weeks, many people feel irritable, "
            "restless or on edge. Appetite can drop, sleep can be broken, and dreams often become "
            "vivid or strange. Some people feel low, sweaty or just uncomfortable in their own skin.",
            "For most people these feelings are strongest early on and usually ease over a couple "
            "of weeks. Knowing what to expect helps: a bad night or a short temper is part of the "
            "process, not proof that you can't do this.",
            "If anxiety, low mood or sleep problems feel severe or aren't easing, talk to a doctor. "
            "A quick daily check-in will help you notice how things are changing from one day to "
            "the next, so you can see the hard patches pass instead of only feeling them.",
        ], A('Do today\'s check-in', 'accounts:daily_checkin',
             detail='Rate your mood, cravings and energy. It takes under a minute.'),
            "Which withdrawal feeling are you most worried about, and what could help with it?"),
        L('Clear out the gear', [
            "When cannabis is in the house, every hard moment becomes a negotiation. Getting rid of "
            "it, and the things you used it with, takes that option off the table. Pipes, papers, "
            "grinders, vape pens, cartridges, edibles hidden in a drawer: all of it.",
            "This can feel oddly emotional, especially if some of it was expensive or meant "
            "something to you. That's normal. You're not throwing away a part of yourself. You're "
            "making room for a version of you that doesn't need any of it.",
            "Do it in one go if you can, and take it out of the house rather than tucking it away. "
            "If a craving shows up while you clear things out, pause, use the Craving SOS tools, "
            "and then carry on once the wave has passed.",
        ], A('Open Craving SOS', 'core:craving_sos',
             detail='Try the breathing exercise once now, so you know it when you need it.'),
            "What would be the hardest thing to throw away, and why?"),
        L('Delete the easy route', [
            "Cannabis can be very easy to get. A dispensary on the way home, a delivery app on your "
            "phone, a number you can text in seconds. When it's that close, a passing urge can turn "
            "into a purchase before you've had time to think.",
            "Today, add some distance. Delete delivery apps and unsubscribe from shop emails and "
            "texts. Block or remove dealer contacts. If you pass a dispensary on your usual route, "
            "plan a different way home for now.",
            "Write down where it was easiest for you to get, and what you'll change about each one. "
            "Mapping your triggers, including the places, people, apps and times of day, makes "
            "these choices clearer and helps you spot the gaps you might have missed.",
        ], A('Fill in the Trigger Map', 'resources:worksheet_detail', ('trigger-map',),
             detail='List the people, places, apps and times that make it easy to buy.'),
            "Which shortcut to buying will you remove today?"),
        L('Mornings without it', [
            "If you used to smoke or vape first thing, mornings can feel strange now. That first "
            "hit may have been how you got out of bed, faced the day or took the edge off. Without "
            "it, there is a gap, and gaps tend to fill with cravings if you leave them empty.",
            "Give your morning a new shape. Get up, drink some water, open a window, step outside "
            "for a few minutes, eat something even if your appetite is low. Small, repeatable steps "
            "work better than a perfect routine.",
            "Plan tomorrow morning tonight, so you aren't making decisions while a craving is "
            "talking. Talking it through with Anchor, the AI coach, can help you build a simple "
            "routine that fits your real life, your schedule and your energy levels right now.",
        ], A('Talk to Anchor', 'accounts:recovery_coach',
             detail='Ask Anchor to help you plan a simple morning routine for this week.'),
            "What is one small thing you can do in the first ten minutes of tomorrow?"),
        L('Rebuilding sleep', [
            "For many people, cannabis became the way to fall asleep. Stopping can mean lying awake, "
            "waking often or having intense dreams for a while. It's one of the most common reasons "
            "people go back, so it's worth giving sleep real attention.",
            "Keep the same bedtime and wake time each day. Dim screens and lights in the last hour. "
            "Try a warm shower, a book or quiet music instead of scrolling. If you can't sleep, get "
            "up for a bit and come back when you feel drowsy.",
            "A short review at the end of each day can also help your mind settle before bed, so "
            "you aren't replaying everything in the dark. Be patient with yourself while your sleep "
            "finds its rhythm. If sleep problems are severe or don't ease, talk to a doctor.",
        ], A('Try the Nightly Review', 'resources:worksheet_detail', ('nightly-review',),
             detail='Spend five minutes reflecting on today before you turn out the light.'),
            "What would a calm last hour before bed look like for you?"),
        L('When a craving hits', [
            "Cravings can feel like they'll keep building until you give in, but they don't. A "
            "craving rises, peaks and falls, often faster than you'd expect. Your job is to ride "
            "out the peak, not to fight it forever.",
            "Notice the urge without acting on it. Breathe slowly, move your body, change rooms, "
            "drink something cold, text someone. Each time you let a craving pass, you learn that "
            "you can, and that makes the next one a little easier.",
            "Keep a short log of your cravings this week: the time, the place, how strong it felt "
            "and what you did. Patterns often show up quickly once you start writing them down, "
            "and they tell you exactly where to plan ahead.",
        ], A('Start an Urge Log', 'resources:worksheet_detail', ('urge-log',),
             detail='Note when each urge came, how strong it was and what you did.'),
            "When did your strongest craving this week happen, and what was going on around you?"),
        L('Filling the evenings', [
            "Evenings are often the hardest part. If cannabis was how you wound down, the hours "
            "after work or dinner can stretch out and feel empty. Boredom is one of the biggest "
            "triggers people describe, and it deserves a plan, not just willpower.",
            "Make a short list of things you can do with your hands, your body or your mind: cook "
            "something new, walk, play music, draw, fix something, call a friend, watch a film you "
            "actually chose. It doesn't need to be exciting, just something.",
            "Put the list somewhere you'll see it around the time evenings get hard. Looking at the "
            "bigger balance of your life, like work, rest, people, health and fun, can also help you "
            "spot what's been missing and what you'd like more of.",
        ], A('Fill in the Lifestyle Balance Wheel', 'resources:worksheet_detail', ('lifestyle-balance-wheel',),
             detail='Rate each area of your life and pick one to give more time this week.'),
            "What used to interest you before cannabis took up your evenings?"),
        L('Feelings without the filter', [
            "Cannabis can quietly turn the volume down on feelings. When you stop, anxiety, anger, "
            "sadness or restlessness may come back louder than you remember. That can be "
            "unsettling, but it usually means you're feeling things fully again, not that something "
            "is broken.",
            "Name what you feel, even just to yourself. Write it down, talk it through, move your "
            "body, or sit with it for a few minutes. Feelings pass more easily when they're allowed "
            "somewhere to go.",
            "Writing a feeling down can help you see what set it off and what you told yourself "
            "about it. If anxiety or low mood feels severe or isn't easing, talk to a doctor. If "
            "you ever think about harming yourself, call or text 988 right away.",
        ], A('Write a thought record', 'resources:worksheet_detail', ('abc-thought-record',),
             detail='Pick one strong feeling from today and trace what set it off.'),
            "Which feeling has surprised you most since you stopped?"),
        L('Friends who smoke', [
            "For many people, cannabis is tied up with friendship. Smoking together might be how "
            "you relax, how you catch up, or the whole point of hanging out. Stopping can make "
            "those friendships feel uncertain, and that can be lonely.",
            "You don't have to end every friendship. You might see some friends in different "
            "settings, like a walk, a meal or a game in the daytime. Others may not respect your "
            "choice, and stepping back from them for now is allowed.",
            "It also helps to meet people who aren't using. Others in recovery understand this "
            "exact problem, because many of them have faced it too. A group can give you somewhere "
            "to talk on the nights your old plans would have involved smoking.",
        ], A('Join a group', 'accounts:groups_list',
             detail='Find a recovery group where you can talk with people who get it.'),
            "Which friendship do you want to keep, and how could you spend time together differently?"),
        L('Tell someone in your corner', [
            "Quitting quietly can work for a while, but it's harder alone. One person who knows "
            "what you're doing can make a real difference: someone to text on a rough night, or "
            "who simply asks how it's going.",
            "Choose someone you trust who won't lecture you. You don't have to share everything. "
            "Something simple works: \"I've stopped smoking weed and it's harder than I thought. "
            "Can I message you when it gets tough?\"",
            "You can also invite them as a supporter here, so they can follow along and encourage "
            "you as you go. Even one message from someone in your corner can change how a hard "
            "evening feels.",
        ], A('Invite a supporter', 'accounts:supporter_invite',
             detail='Send an invite to one person you trust to cheer you on.'),
            "Who is one person you'd feel safe telling about this?"),
        L('If you slip', [
            "A slip doesn't erase what you've done. Every day you've gone without cannabis still "
            "happened, and everything you've learned is still yours. A slip is something to learn "
            "from, not a verdict about who you are or what you can do.",
            "If it happens, reach out quickly instead of hiding it. Then get curious: what was "
            "going on, what were you feeling, what made it easy? Those answers point to the next "
            "thing to change, and you can use them the very same day.",
            "Writing a simple plan now, while things are steady, means you'll know what to do if a "
            "hard moment comes. Include your early warning signs, the people you'll contact, and "
            "the first few steps you'll take to get back on track.",
        ], A('Build your relapse plan', 'accounts:relapse_plan',
             detail='Write down your warning signs and who you will contact.'),
            "What would you want to tell yourself the morning after a slip?"),
        L('Noticing what\'s coming back', [
            "Somewhere in the second week, many people start to notice changes. Thoughts feel a "
            "little clearer. Memory for conversations and plans gets sharper. Motivation creeps "
            "back. Money that used to disappear stays in your account.",
            "These changes can be gradual and easy to miss, so take a moment to look for them. Add "
            "up what you would have spent. Notice the things you've remembered or followed through "
            "on. Small wins count.",
            "Marking progress helps you hold onto it, especially on harder days when it's easy to "
            "forget why you started. Pick one change you've noticed, however small, and record it "
            "so you can look back on it later.",
        ], A('Add a milestone', 'accounts:add_milestone',
             detail='Record a win from this week, like money saved or a good night\'s sleep.'),
            "What is one thing that has improved since you stopped, even slightly?"),
        L('Two weeks, and what comes next', [
            "Two weeks ago you decided to stop using cannabis. Look back at what you've done since: "
            "nights you got through, apps you deleted, cravings you rode out, feelings you let "
            "yourself feel. Whatever your count says today, you know much more about your patterns.",
            "The next stretch is about keeping what works. Keep your pledge, your check-ins and "
            "your plan for hard moments. The First 30 Days program builds on everything here, and "
            "meetings and the community give you people to lean on as things settle.",
            "Take a moment to mark this. Write down what surprised you, what has been hardest and "
            "what you want to protect. A meeting is a good place to keep going, whatever path you "
            "follow. Then carry on, one day at a time.",
        ], A('Find a meeting', 'support_services:meeting_list',
             detail='Look for an online or in-person meeting that fits your path.'),
            "What do you want to remember about these two weeks when the next hard day comes?"),
    ),
)
