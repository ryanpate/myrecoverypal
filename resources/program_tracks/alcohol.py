from resources.program_types import A, L, Program

TRACK = Program(
    slug='alcohol-14-days',
    title='Quitting Alcohol: 14 Days',
    icon='🍃',
    summary='A two-week, day-by-day guide to stopping drinking and building evenings, weekends and friendships that work without alcohol.',
    intro=(
        "These fourteen short lessons walk you through the first two weeks without alcohol: sleep, "
        "social pressure, the after-work drink, weekends, and the people you used to drink with. "
        "One important safety note first: if you have been drinking heavily or every day, stopping "
        "suddenly can cause dangerous withdrawal, including seizures, so please talk to a doctor "
        "before or while you stop. Medical detox exists for exactly this, and medications for "
        "alcohol use disorder are worth asking a doctor about too."
    ),
    audience='Anyone who wants to stop drinking, or take a serious break from it, and would like a steady day-by-day guide for the first two weeks.',
    meta_description='Free 14-day quit drinking program: first 3 days free. Daily lessons on sleep, social pressure, alcohol-free evenings and staying sober.',
    weeks=(
        'Week 1: Getting through the early days',
        'Week 2: Building a life that works without it',
    ),
    free_days=3,
    kind='track',
    substance='Alcohol',
    helplines=(
        ('SAMHSA National Helpline (free, 24/7)', '1-800-662-4357'),
        ('988 Suicide & Crisis Lifeline', '988'),
    ),
    lessons=(
        L('Starting safely', [
            "Deciding to stop drinking is a big step, and the first thing to get right is safety. "
            "If you have been drinking heavily or daily, stopping all at once can cause dangerous "
            "withdrawal, including seizures. That isn't a reason to keep drinking. It's a reason to "
            "talk to a doctor before or while you stop, so you have support if your body reacts.",
            "Medical detox exists so people can stop safely with care around them. A doctor can also "
            "tell you about medications for alcohol use disorder, which can make the early weeks "
            "easier for some people. Asking about them is not cheating; it is using every tool "
            "available. If you're unsure where to start, the SAMHSA National Helpline is free and "
            "open around the clock.",
            "If you drank lightly or occasionally, you may feel little more than restlessness. "
            "Either way, watch for shaking, sweating, confusion, a racing heart or seeing things "
            "that aren't there. Those are signs to get medical help right away, and if anything "
            "feels like an emergency, call 911.",
        ], A('Find a doctor or treatment', 'resources:professional_help',
             detail='Look up a doctor, detox or treatment option near you, or save one for later.'),
            "Who could you tell today that you are stopping, so someone knows to check on you?"),
        L('Why you are stopping', [
            "In the first days, the reasons that made you stop can fade fast, especially around "
            "the time you'd usually pour a drink. Writing your reason down gives it somewhere to "
            "live outside your head, where it can't quietly get argued away at six in the evening.",
            "Your reason can be simple. Waking up clear-headed. Being present for your kids. "
            "Stopping the 3 a.m. worry. Feeling like yourself again. It doesn't have to impress "
            "anyone; it only has to matter to you, and it's fine if it changes or grows over time.",
            "The daily pledge on your home screen holds your reason and an optional photo, and it "
            "shows them to you each morning. Taking the pledge takes one tap, and the streak it "
            "builds becomes something worth protecting.",
        ], A("Take today's pledge", 'accounts:progress',
             detail='Tap the pledge and add your reason for stopping, in your own words.'),
            "What do you most want your mornings to feel like a month from now?"),
        L('Sleep in the first weeks', [
            "Many people drink to fall asleep, so it can be a shock when the first nights without "
            "alcohol are restless. You might lie awake, wake often, or have vivid dreams. This is "
            "common and usually settles as your body adjusts. Alcohol may have knocked you out, but "
            "it rarely gave you deep, restful sleep.",
            "Help your body along. Keep the same bedtime and wake time, dim the lights an hour "
            "before bed, and put your phone across the room. Cut caffeine after lunch. A warm "
            "shower, an herbal tea or a few slow breaths can stand in for the nightcap.",
            "If sleep stays very poor, or you feel unwell, mention it to a doctor rather than "
            "reaching for anything on your own. Meanwhile, a quick daily check-in lets you track "
            "how your sleep and energy are changing.",
        ], A("Do today's check-in", 'accounts:daily_checkin',
             detail='Rate your mood, cravings and energy, and note how you slept.'),
            "What is one small change you could make to your evening tonight to help you sleep?"),
        L('The after-work drink', [
            "For many people the strongest pull comes at the same time every day: the end of the "
            "workday, the walk through the door, the moment the kids are in bed. That drink was "
            "doing a job. It marked the line between work and rest and told your body it could "
            "finally relax.",
            "The job still needs doing, just by something else. Change clothes the moment you get "
            "home. Take a ten-minute walk. Make a proper drink in a nice glass, something cold and "
            "fizzy or warm and spiced. Put on music. The point is a clear signal that the day is "
            "over.",
            "Notice exactly when and where the urge shows up. Mapping your triggers turns a vague "
            "dread into a short list you can plan around, one by one. Once you can see the pattern, you "
            "can put a new ritual exactly where the old drink used to be.",
        ], A('Fill in the Trigger Map', 'resources:worksheet_detail', ('trigger-map',),
             detail='List the times, places, people and feelings that make you want a drink.'),
            "What could you do in the first fifteen minutes after work that would tell your body the day is done?"),
        L('Riding out a craving', [
            "A craving can feel like it will keep building until you give in. It won't. Urges rise, "
            "peak and pass, often faster than you expect. Each time you wait one out, you teach "
            "your brain that you can feel the pull and still choose something else.",
            "When a wave comes, delay first. Tell yourself you'll decide in twenty minutes. Then "
            "drink a glass of water, eat something, step outside, or text someone. Hunger, "
            "tiredness and loneliness all make cravings louder, so look after those first.",
            "Craving SOS has a breathing exercise, urge surfing and grounding, all in one place. "
            "Try one now while you feel calm, so it's familiar when you really need it. Practicing in a calm moment makes it far easier "
            "to remember the steps when your mind is busy with the urge.",
        ], A('Open Craving SOS', 'core:craving_sos',
             detail='Try the breathing exercise once now, while things are calm.'),
            "What has helped you get through a craving before, even a little?"),
        L('What to say when someone offers you a drink', [
            "Drinking is woven into so much social life that turning one down can feel awkward at "
            "first. The good news is that most people care far less than you fear. A short, "
            "relaxed answer usually ends the conversation before it begins, and the attention moves "
            "on within seconds.",
            "Have a few lines ready. \"I'm good, thanks.\" \"Not tonight.\" \"I'm taking a break.\" "
            "\"I'm driving.\" You don't owe anyone a full explanation. Holding a drink of your own, "
            "even sparkling water with lime, means fewer people ask in the first place.",
            "If someone keeps pushing, that says more about them than about you. It is completely "
            "fine to leave early. Practicing your answers with Anchor can make them feel natural "
            "before you're on the spot, so the words come easily when you need them.",
        ], A('Practice with Anchor', 'accounts:recovery_coach',
             detail='Ask Anchor to role-play someone offering you a drink, and try out your answers.'),
            "Which line would feel most natural for you to say out loud?"),
        L('A plan for hard moments', [
            "Even with good intentions, hard moments come: a bad day, a fight, a celebration, a "
            "wave of boredom. They're much easier to handle when you've decided ahead of time what "
            "you'll do, instead of trying to think clearly while the urge is loud.",
            "A relapse prevention plan is simply that decision written down. Your warning signs, "
            "the people you'll contact, the places you'll go, and the things you'll do instead. "
            "Keep it short enough that you would actually read it in a tough moment.",
            "And if you do drink, treat it as information, not failure. Reach out quickly, look at "
            "what led up to it, and start again the next day. If you drank heavily again, the "
            "same safety note applies: talk to a doctor before stopping.",
        ], A('Build your relapse plan', 'accounts:relapse_plan',
             detail='Write down your warning signs, your people and your first steps.'),
            "What is the earliest sign that you are heading toward a drink?"),
        L('Noticing what is changing', [
            "A week or so in, many people start to notice small changes. Mornings feel clearer. "
            "Energy is steadier. Skin may look less puffy. Sleep often starts to improve. These "
            "changes are easy to miss unless you look for them, and they're powerful reminders of "
            "why you started.",
            "Money is one of the most concrete. Add up what you'd usually spend on alcohol in a "
            "week, including the takeout, the ride home and the next-day snacks. Set that money aside "
            "for something you actually want.",
            "Marking progress matters. Recording a milestone, even one week, gives you something "
            "real to look back on when motivation dips. Write down what you've noticed so far, in your "
            "own words, so future you can see how far you've already come.",
        ], A('Add a milestone', 'accounts:add_milestone',
             detail='Record your first week, or any change you have noticed so far.'),
            "What is one change, however small, that you've noticed since you stopped?"),
        L('Weekends, parties and holidays', [
            "Weekends can feel strangely long without drinking, and parties and holidays bring "
            "extra pressure. Planning ahead helps a lot. Decide before you arrive what you'll drink "
            "instead, how long you'll stay, how you'll get home, and who you can text if it gets "
            "hard.",
            "Give yourself an exit. Arrive a little late, leave a little early, and know that "
            "nobody keeps score. Bringing your own alcohol-free drinks means you're never stuck "
            "with tap water. Morning plans, like a breakfast or a hike, give you a reason to head "
            "home.",
            "Fill the gaps too. Weekends used to have drinking as their center. Try planning one "
            "thing each weekend that you'd genuinely look forward to, and that's easier sober. A balanced week, with rest, movement, people and fun in it, leaves "
            "much less empty space for old habits to fill.",
        ], A('Look at the balance in your life', 'resources:worksheet_detail', ('lifestyle-balance-wheel',),
             detail='Rate each area of your life and pick one to put more weekend time into.'),
            "What is one thing you could plan for this weekend that you'd enjoy more without a drink?"),
        L('The people you drank with', [
            "Some friendships were built around drinking, and stopping can make them feel "
            "uncertain. Some friends will be supportive straight away. Some may tease, push or "
            "drift off. Others may surprise you. None of this means you've done anything wrong; "
            "you're just changing the shape of the time you spend together.",
            "Suggest plans that don't center on a bar: coffee, a walk, a film, a game. Notice "
            "which friendships still feel good. It's okay to step back from people who keep "
            "pressing you to drink, at least for now.",
            "Bringing in someone who's firmly on your side helps. Inviting a loved one as a "
            "supporter lets them follow your progress and cheer you on. Having even one person who knows what you're doing, and is glad about it, "
            "can make the harder conversations feel much easier.",
        ], A('Invite a supporter', 'accounts:supporter_invite',
             detail='Invite a friend or family member you trust to support you.'),
            "Which person in your life would be glad to hear that you've stopped drinking?"),
        L('You are not alone in this', [
            "Stopping drinking can feel lonely, especially if many of your social plans involved "
            "alcohol. Being around people who understand makes a real difference. They know what "
            "a Friday night craving feels like, and they won't ask why you're not drinking.",
            "There are many kinds of meetings, from 12-step groups to SMART and other secular "
            "options, online and in person. You don't have to share anything at your first one. "
            "Just listening is enough, and it's fine to try a few before one feels right.",
            "Community inside the app counts too. Groups and the social feed are full of people "
            "doing the same thing you are, one day at a time. Reading how someone else got through a "
            "tough Friday night can be exactly what you need on yours.",
        ], A('Find a meeting', 'support_services:meeting_list',
             detail='Browse meetings online or near you and pick one to try this week.'),
            "What would make it easier for you to walk into, or log into, your first meeting?"),
        L('Thinking traps', [
            "Your mind will sometimes make a convincing case for a drink. \"Just one won't hurt.\" "
            "\"I've had a terrible day, I deserve it.\" \"I was never that bad anyway.\" These "
            "thoughts are normal, and they don't have to be obeyed. They tend to show up most "
            "when you're tired, stressed or celebrating.",
            "One useful habit is to play the tape forward. Picture not just the first drink but "
            "the rest of the night, and the next morning. The story usually looks different once "
            "you follow it all the way through.",
            "Writing a thought down and questioning it takes some of its power away. A thought "
            "record gives you a simple structure for doing exactly that. The more often you practice, the quicker you'll spot these "
            "thoughts for what they are when they show up uninvited.",
        ], A('Try the ABC Thought Record', 'resources:worksheet_detail', ('abc-thought-record',),
             detail='Pick one drinking thought from this week and work it through.'),
            "What does your mind most often say to talk you into a drink?"),
        L('Talking it through', [
            "Some days the hardest part isn't a craving but the feelings underneath: stress, "
            "grief, boredom, anger. Alcohol may have been your way of turning the volume down. "
            "Without it, those feelings are louder for a while, and they need somewhere to go.",
            "Talking helps. A friend, a sponsor, a counselor, a meeting, or a quick post asking "
            "how others handle tough evenings. Sharing what you're going through often makes it "
            "lighter, and it helps someone else feel less alone too.",
            "If you ever feel hopeless or think about hurting yourself, call or text 988 right "
            "away. You deserve support, and it is there day and night. In an emergency, call 911. Reaching out is a sign of "
            "strength, never something to feel ashamed of.",
        ], A('Share on the feed', 'accounts:social_feed',
             detail='Post how your first two weeks are going, or ask how others get through evenings.'),
            "What feeling have you noticed more since you stopped drinking?"),
        L('Two weeks, and what comes next', [
            "Two weeks ago you decided to stop drinking. Look back at what you've done since: "
            "nights you got through, offers you turned down, evenings you rebuilt, people you let "
            "in. Whatever your count says today, you've learned a great deal about your patterns "
            "and what helps.",
            "The next stretch is about keeping what works. Keep your pledge, your check-ins and "
            "your plan for hard moments. The First 30 Days program builds on everything here, and "
            "meetings and groups give you people to lean on as things settle.",
            "Take a moment to mark this. Write down what has surprised you, what has been hardest "
            "and what you want to protect. Then carry on, one day at a time, "
            "knowing you don't have to do any of it alone. The people you've met here will still be "
            "here tomorrow.",
        ], A('Join a group', 'accounts:groups_list',
             detail='Find a recovery group to join for the weeks ahead.'),
            "What do you want to remember about these two weeks when the next hard day comes?"),
    ),
)
