from resources.program_types import A, L, Program

TRACK = Program(
    slug='gambling-14-days',
    title='Quitting Gambling: 14 Days',
    icon='🎲',
    summary='A two-week, day-by-day guide to stopping gambling, cutting off access, facing money honestly and filling the space betting used to take.',
    intro=(
        "These fourteen short lessons walk you through the first two weeks without gambling, "
        "whether that meant casinos, sports betting, betting apps, lottery tickets or scratch-offs. "
        "You'll cut off access, put guardrails around your money, learn to ride out urges and "
        "start rebuilding trust. If you ever feel hopeless or think about harming yourself, call "
        "or text 988 any time, day or night."
    ),
    audience='Anyone who wants to stop gambling or betting of any kind and would like a steady day-by-day guide for the first two weeks.',
    meta_description='Free 14-day quit gambling program: first 3 days free. Daily lessons on blocking betting apps, urges, chasing losses, debt and staying gamble-free.',
    weeks=(
        'Week 1: Cutting off access and riding out urges',
        'Week 2: Facing money, rebuilding trust and filling the gap',
    ),
    free_days=3,
    kind='track',
    substance='Gambling',
    helplines=(
        ('National Problem Gambling Helpline', '1-800-GAMBLER'),
        ('988 Suicide & Crisis Lifeline', '988'),
    ),
    lessons=(
        L('Day one, and why you are here', [
            "Deciding to stop gambling takes real courage, especially if losses have piled up or "
            "you've tried before. Whatever brought you here, a bad weekend, a hidden debt or a "
            "quiet feeling that it has gone too far, you don't have to fix everything today. "
            "Today you only need to stay gamble-free and start putting some protection in place.",
            "Gambling problems can bring heavy feelings: shame, panic about money, a sense that "
            "there's no way out. Those feelings are common and they do ease. If you ever think "
            "about harming yourself, call or text 988 right away. The National Problem Gambling "
            "Helpline at 1-800-GAMBLER is also free and confidential, any hour.",
            "Write down your reason for stopping. It can be simple: your family, your peace of "
            "mind, or being tired of lying awake doing sums. Your daily pledge can show that "
            "reason to you every morning, so it's there before the day's first urge.",
        ], A('Take today\'s pledge', 'accounts:progress',
             detail='Tap the pledge card and add your reason for stopping gambling.'),
            "What is the one reason for stopping that you most want to remember on a hard day?"),
        L('Cut off access first', [
            "The single most powerful early step is making gambling harder to reach. Urges come "
            "fast, and a betting app on your phone can turn a passing thought into a bet in "
            "seconds. Putting distance between the urge and the action gives your better judgment "
            "time to catch up.",
            "Today, delete every betting and casino app, and close the accounts behind them rather "
            "than just logging out. Many casinos and betting sites offer self-exclusion programs "
            "that block you from playing for a set period; sign up for every one that applies to "
            "you. Gambling-blocking software for your phone and computer adds another wall.",
            "It can feel drastic, even a little frightening, to close those doors. That feeling "
            "is normal. You aren't losing anything you need. You're taking away the easy route on "
            "the days when your resolve is thin, so you don't have to rely on willpower alone.",
        ], A('Do today\'s check-in', 'accounts:daily_checkin',
             detail='Log your mood and urges, and note which apps or accounts you closed today.'),
            "Which way of gambling is still easiest for you to reach, and how could you close it off?"),
        L('Put guardrails around your money', [
            "Once the apps are gone, look at the money itself. Ask your bank whether it can block "
            "gambling transactions on your cards; many banks offer this and can set it up quickly. "
            "Carry only the cash you need for the day, and leave extra cards at home, so a sudden "
            "urge has nothing to work with.",
            "Many people find it helps to let a trusted person share oversight of their money for "
            "a while. That might mean they hold a spare card, look over statements with you, or "
            "help you decide on larger spending. It isn't a punishment. It's a temporary support "
            "while new habits settle in.",
            "Choosing who to ask can be the hardest part. Pick someone steady who wants good things "
            "for you. You can invite them here as a supporter, so they can follow your progress and "
            "cheer you on without you having to explain everything each time.",
        ], A('Invite a supporter', 'accounts:supporter_invite',
             detail='Send an invite to one trusted person who can support you through these weeks.'),
            "Who in your life could you trust to help keep an eye on money with you for a while?"),
        L('When the urge to bet hits', [
            "An urge to gamble can feel urgent and certain, as if you must act right now. Urges "
            "rise, peak and fade, often more quickly than you expect. The goal isn't to argue with "
            "the urge. It's to get through the peak without placing a bet.",
            "When one arrives, change something straight away: stand up, step outside, drink a "
            "glass of water, text someone, or put your phone in another room. Name it to yourself: "
            "this is an urge, and it will pass. Watching it rise and fall like a wave is a skill "
            "that grows stronger with practice.",
            "Know where to go before you need it. Craving SOS has breathing, urge surfing and "
            "grounding tools you can open in a moment. Try one now while things are calm, so it "
            "feels familiar when a strong urge comes.",
        ], A('Open Craving SOS', 'core:craving_sos',
             detail='Try the urge surfing or breathing exercise once now, while you feel calm.'),
            "What has helped you get through an urge to gamble before, even for a few minutes?"),
        L('Chasing losses and the big-win story', [
            "One of the most powerful thoughts in gambling is that the next bet could win it all "
            "back. If you could just land one big win, the debt would vanish and nobody would ever "
            "need to know. That thought feels like a plan. In reality it's the urge talking, "
            "dressed up as a solution.",
            "Chasing losses usually deepens the hole, and the big-win story keeps you tied to the "
            "very thing causing the damage. The way out of money trouble is slower and steadier: "
            "stopping, facing the numbers and making a plan. It's less exciting, and it actually "
            "works.",
            "When the thought shows up, write it down and look at it on paper. What is it "
            "promising? What happened the last times you believed it? A thought record helps you "
            "catch these patterns and answer them with something more honest.",
        ], A('Fill in a thought record', 'resources:worksheet_detail', ('abc-thought-record',),
             detail='Write down one "I can win it back" thought and test it against what really happened.'),
            "What does the \"one big win\" thought promise you, and what has it actually delivered?"),
        L('Know your triggers', [
            "Triggers are the moments that make gambling feel more tempting. For many people they "
            "include sports seasons and big games, gambling ads, payday, a win or loss someone "
            "mentions, boredom, loneliness, stress or a fight at home. Some are loud and obvious; "
            "others slip in quietly.",
            "You can't remove every trigger from your life, especially ads and sport. What you can "
            "do is stop being caught off guard. When you know payday is a risky day, or that a "
            "Saturday afternoon alone is hard, you can plan something for it in advance.",
            "Today, map yours. Think about people, places, times, feelings and the things you see "
            "on your screen. It takes about fifteen minutes, and you'll draw on it for the rest of "
            "this program, especially when you build your plan tomorrow.",
        ], A('Fill in the Trigger Map', 'resources:worksheet_detail', ('trigger-map',),
             detail='List the people, places, times, feelings and ads that make you want to gamble.'),
            "Which of your triggers surprised you most when you wrote it down?"),
        L('A plan for the risky moments', [
            "Hard moments are easier when you've already decided what to do. Instead of working it "
            "out mid-urge, you follow a plan you made on a calmer day. That's what a relapse "
            "prevention plan is: your own instructions for the times you're most at risk.",
            "Think about your riskiest moments from yesterday's trigger map. For each one, write a "
            "simple response: who you'll call, where you'll go, what you'll do instead, and how "
            "you'll keep money out of reach. Payday and big sporting weekends deserve a plan of "
            "their own.",
            "You've finished your first week. That matters, whether it went smoothly or had rough "
            "patches. Keep your plan somewhere easy to find, and share it with your supporter if "
            "that feels right, so they know how to help when it counts.",
        ], A('Build your relapse plan', 'accounts:relapse_plan',
             detail='Add your top three risky moments and what you will do in each one.'),
            "What is your riskiest day or time of the week, and what will you do differently then?"),
        L('Facing the numbers', [
            "Many people avoid looking at what gambling has cost because the total feels too "
            "frightening. Not knowing tends to feed anxiety, and anxiety can feed urges. Facing "
            "the numbers honestly, a little at a time, usually brings more relief than you expect.",
            "Sit down somewhere calm, maybe with someone you trust, and list what you owe and to "
            "whom. Then list what is coming in and what has to go out each month. You don't need "
            "to solve it today. Seeing it clearly is the first step toward a plan.",
            "Free, non-profit credit counseling can help you work out a realistic plan and talk to "
            "lenders. A counselor or therapist who understands gambling can also help with the "
            "stress and shame that often sit underneath. Asking for help with money is a strong "
            "step, not a failure.",
        ], A('Find professional help', 'resources:professional_help',
             detail='Look for a counselor or therapist who works with gambling problems.'),
            "What feeling comes up when you think about looking at the full picture of your money?"),
        L('Telling someone the truth', [
            "Gambling often comes with secrecy: hidden accounts, small lies about where money went, "
            "covering for the time spent. Keeping all of that going is exhausting. Telling one "
            "trusted person the truth can lift a weight you may not have realized you were "
            "carrying.",
            "You don't have to share every detail at once. You might start with: I've had a "
            "problem with gambling, I'm stopping, and I'd like your support. If money affects them "
            "too, be honest about that, and let them help with oversight for a while if they are "
            "willing.",
            "Their first reaction may be hurt, anger or worry. That's understandable, and it often "
            "softens as they see you following through. If you're unsure how to begin, Anchor can "
            "help you think through what to say.",
        ], A('Talk it through with Anchor', 'accounts:recovery_coach',
             detail='Ask Anchor to help you plan how to tell someone about your gambling.'),
            "Who is the one person you would most want to know the truth, and what holds you back?"),
        L('Filling the time and the thrill', [
            "Gambling takes up a lot of space: time spent betting, checking scores, planning the "
            "next wager, and the rush of waiting for a result. When it stops, that space can feel "
            "empty and flat. Boredom is one of the most common reasons people go back, so it's "
            "worth planning for.",
            "Look for things that give you some of what gambling gave you. If it was excitement, "
            "try something active or a little challenging. If it was escape, try something "
            "absorbing, like a game, a project or time outdoors. If it was company, find people to "
            "do things with.",
            "A lifestyle balance wheel helps you see which parts of life have been squeezed out, "
            "such as rest, friendships, health or fun, and pick one small thing to bring back this "
            "week. Small, regular changes tend to last longer than big ones.",
        ], A('Try the Lifestyle Balance Wheel', 'resources:worksheet_detail', ('lifestyle-balance-wheel',),
             detail='Rate each area of your life and choose one small thing to add this week.'),
            "What gave you a sense of excitement or calm before gambling took up so much space?"),
        L('If you slip', [
            "If you place a bet after deciding to stop, it doesn't erase the progress you've made. "
            "A slip is an event, not a verdict on who you are. What matters most is what you do "
            "next, and the sooner you reach out, the smaller the slip tends to stay.",
            "Watch out for the thought that says you've blown it, so you might as well keep going. "
            "That's the chasing pattern again. Stop, close off whatever access you used, and tell "
            "your supporter or someone you trust. Then look at what led up to it with curiosity, "
            "not blame.",
            "What were you feeling? What did you see? Was money within easy reach? Each answer "
            "points to something you can strengthen in your plan. If a slip leaves you feeling "
            "hopeless, call or text 988, or call 1-800-GAMBLER.",
        ], A('Update your relapse plan', 'accounts:relapse_plan',
             detail='Add one new step you would take after a slip, or a gap a slip could exploit.'),
            "If you slipped tomorrow, who would you reach out to first, and what would you say?"),
        L('You don\'t have to do this alone', [
            "Gambling problems can be isolating. Many people feel nobody else would understand, or "
            "that they should be able to sort it out quietly by themselves. In truth, plenty of "
            "people have walked this road, and hearing from them can make it feel far less lonely.",
            "Meetings for people stopping gambling happen both online and in person, and they come "
            "in different styles: twelve-step, secular, faith-based and skills-focused. You can "
            "simply listen at first. Nobody expects you to speak until you're ready.",
            "Try one meeting this week, even if you're unsure it's for you. Notice how it feels to "
            "be in a room, or on a screen, with people who get it without needing an explanation. That feeling of being understood can carry you a long way.",
        ], A('Find a meeting', 'support_services:meeting_list',
             detail='Search for a gambling or general recovery meeting, online or near you, this week.'),
            "What would make it easier for you to try a meeting for the first time?"),
        L('Rebuilding trust and noticing what you\'ve saved', [
            "If gambling hurt people close to you, trust may take time to return. Words matter, but "
            "steady actions matter more: being open about money, following through on what you "
            "say, and letting people see your progress. Over weeks and months, those small things "
            "add up.",
            "Notice the money you are no longer losing. Keep a rough running total of what you "
            "would have spent on bets, tickets or deposits. Watching it grow can be a real "
            "encouragement, and it may help with the plan you made for your debts.",
            "Mark the progress you've made. A gamble-free weekend, a first meeting, an honest "
            "conversation or a closed account are all worth recording. Milestones help you see "
            "how far you've come on days that feel slow.",
        ], A('Add a milestone', 'accounts:add_milestone',
             detail='Record one step you\'re proud of, like closing an account or a first gamble-free payday.'),
            "What is one way you've shown someone you can be trusted again this week?"),
        L('Two weeks, and what comes next', [
            "Two weeks ago you decided to stop gambling. Look back at what you've done since: "
            "apps deleted, accounts closed, urges ridden out, numbers faced, maybe a hard "
            "conversation or two. Whatever your count says today, you've learned a great deal "
            "about your patterns and what helps.",
            "The next stretch is about keeping what works. Keep your blocks and money guardrails "
            "in place, along with your pledge, check-ins and plan for risky moments. The First 30 "
            "Days program builds on everything here, and meetings and groups give you people to "
            "lean on.",
            "Take a moment to mark this. Write down what surprised you, what was hardest and what "
            "you want to protect. Then carry on, one day at a time. The National Problem Gambling "
            "Helpline and 988 are always there if you need them.",
        ], A('Join a group', 'accounts:groups_list',
             detail='Find a recovery group to join for the weeks ahead.'),
            "What do you want to remember about these two weeks when the next hard day comes?"),
    ),
)
