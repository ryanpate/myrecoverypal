"""Daily reflection library: short original readings for recovery.

Each reading is two or three short paragraphs plus a journal prompt. The
readings work for any path (12-step, SMART, secular, faith-based), so none
names a program or quotes its literature. All text here is original to
MyRecoveryPal. Don't paste readings from published daily-meditation books,
which are copyrighted.

One reading is "today's" for everyone, chosen by a deterministic rotation
over the member's local date (`todays_reflection`). Access (see
reflection_views.py):
    free     today's reading in full, the opening paragraph of the rest
    premium  the full library, favorites, and "Reflect in journal" on any
             reading
Keep the first paragraph of each reading able to stand on its own, since
it's the free preview.
"""
from dataclasses import dataclass

from django.utils import timezone

THEMES = {
    'early-days': 'Early days',
    'cravings': 'Cravings & urges',
    'feelings': 'Feelings',
    'relationships': 'Relationships',
    'self-compassion': 'Self-compassion',
    'purpose': 'Purpose & values',
    'gratitude': 'Gratitude & joy',
    'resilience': 'Setbacks & resilience',
}


@dataclass(frozen=True)
class Reflection:
    slug: str
    title: str
    theme: str
    paragraphs: tuple
    prompt: str

    @property
    def theme_label(self):
        return THEMES[self.theme]

    @property
    def preview(self):
        return self.paragraphs[0]

    @property
    def text(self):
        return '\n\n'.join(self.paragraphs)


R = Reflection

REFLECTIONS = [
    # --- Early days -------------------------------------------------------
    R('just-today', 'Just today', 'early-days', (
        "Forever is too heavy to carry. When the thought of never again shows up, it can make "
        "the whole effort feel impossible before the morning is over.",
        "Today is a size you can hold. You don't have to promise anything about next year. You "
        "only have to get through these hours without using, and then you can decide about "
        "tomorrow tomorrow.",
        "Most long stretches of recovery are made of ordinary days that someone simply finished.",
    ), "What would make getting through just today a little easier?"),
    R('the-fog-lifts', 'The fog lifts slowly', 'early-days', (
        "Early recovery can feel worse before it feels better. Sleep is strange, feelings arrive "
        "at full volume, and the relief you were promised hasn't shown up yet.",
        "That doesn't mean it isn't working. Your body and brain are recalibrating after a long "
        "time running on something else, and that takes weeks and months, not days.",
        "Notice small signs: a morning that started without dread, a conversation you remember "
        "clearly, money still in your account on Friday. These are the first patches of clear sky.",
    ), "What is one small thing that is already better than it was?"),
    R('ask-for-help', 'Asking is a strength', 'early-days', (
        "Many of us got good at handling everything alone, or at looking like we were. Asking for "
        "help can feel like admitting defeat.",
        "In recovery it's the opposite. Reaching out before a hard moment is one of the most "
        "skilled things a person can do. It takes honesty, humility and planning, all at once.",
        "You don't need the perfect words. \"I'm having a rough day, can you talk?\" is enough.",
    ), "Who could you reach out to this week, even just to say hello?"),
    R('new-routines', 'Filling the empty hours', 'early-days', (
        "When using stops, it leaves gaps: the evening hours, the drive home, the weekend that "
        "used to have a shape. Empty time is where old habits wait.",
        "You don't need a perfect schedule. You need a few reliable things to put in the gaps: a "
        "walk, a meeting, a call, a meal you cook, a show you save for that hour.",
        "New routines feel awkward at first. Repetition is what makes them yours.",
    ), "Which time of day feels emptiest, and what could you put there?"),

    # --- Cravings & urges -------------------------------------------------
    R('urges-are-waves', 'Urges are waves', 'cravings', (
        "A craving can feel like it will keep building until you give in. It won't. Urges rise, "
        "peak and fall, usually within half an hour, whether or not you act on them.",
        "Each time you ride one out, you teach your brain that the wave passes on its own. The "
        "next one is often a little smaller.",
        "Breathe, move, call someone, change rooms. You only need to outlast the peak.",
    ), "What has helped you ride out an urge before?"),
    R('play-the-tape', 'Play the tape forward', 'cravings', (
        "Cravings are good salespeople. They show you the first few minutes: the relief, the "
        "warmth, the escape. They never show you the rest.",
        "When the pitch starts, play the whole tape. Picture the hour after, the next morning, "
        "the messages you'd have to send, the count starting over.",
        "Seeing the full story doesn't make the urge vanish, but it gives the rest of you a "
        "vote.",
    ), "What does the end of the tape look like for you?"),
    R('halt', 'Hungry, angry, lonely, tired', 'cravings', (
        "Sometimes a craving isn't really about the substance. It's your body or mind asking for "
        "something simpler.",
        "Before deciding what an urge means, check the basics. Have you eaten? Are you carrying "
        "anger you haven't said out loud? Have you talked to anyone today? When did you last "
        "really rest?",
        "A sandwich, a phone call or an early night won't solve everything, but they solve more "
        "than you'd expect.",
    ), "Which of the four shows up most often for you?"),
    R('triggers-are-information', 'Triggers are information', 'cravings', (
        "Getting triggered doesn't mean you're failing. It means something in your life is "
        "connected to using, and now you know where.",
        "Treat each trigger like a clue. What time was it? Who was there? What were you feeling "
        "just before? Over time the clues form a map.",
        "With a map, you can plan your route: avoid some places, change others, and bring support "
        "to the ones you can't avoid.",
    ), "What did your last trigger teach you?"),

    # --- Feelings ---------------------------------------------------------
    R('feelings-arent-facts', "Feelings aren't facts", 'feelings', (
        "Feeling like a failure doesn't make you one. Feeling hopeless doesn't mean nothing will "
        "change. Feelings are real, but they're weather, not climate.",
        "Without something to numb them, emotions can feel enormous. Let them be what they are: "
        "signals worth listening to, not orders you have to follow.",
        "Name the feeling, notice where it sits in your body, and give it a little time. It will "
        "shift.",
    ), "What feeling has been loudest this week, and what might it be telling you?"),
    R('boredom', 'Making peace with boredom', 'feelings', (
        "Boredom catches a lot of people off guard. Life without the highs and crashes can feel "
        "flat, and flat can feel dangerous.",
        "Some of that flatness is your brain relearning how to enjoy ordinary things. Pleasure in "
        "small things comes back gradually, and it comes back faster when you keep showing up for "
        "them.",
        "Try something new, even something small. Boredom is often an invitation to grow.",
    ), "What is something you've always wanted to try?"),
    R('anger', 'Anger has something to say', 'feelings', (
        "Anger is not the enemy. It often points at something real: a boundary crossed, a need "
        "ignored, an old hurt still open.",
        "The trouble starts when anger is held in until it explodes, or carried around until it "
        "becomes a reason to use.",
        "Say it to someone safe, write it out, walk it off. Then ask what the anger is protecting.",
    ), "What is your anger trying to protect right now?"),
    R('shame-vs-guilt', 'Guilt and shame', 'feelings', (
        "Guilt says, \"I did something wrong.\" Shame says, \"I am something wrong.\" Guilt can "
        "lead to repair. Shame mostly leads to hiding.",
        "Many of us carry a heavy load of shame from the years of using. It grows in secrecy and "
        "shrinks when it's spoken to someone who listens without judging.",
        "You can take responsibility for what you did without deciding you're beyond repair.",
    ), "Is there something you've been carrying alone that you could share with someone safe?"),

    # --- Relationships ----------------------------------------------------
    R('rebuilding-trust', 'Trust is rebuilt in small deposits', 'relationships', (
        "After years of broken promises, the people who love you may not believe you right away. "
        "That can hurt, especially when you're working hard.",
        "Trust comes back the way it left: slowly, through repeated actions. Showing up on time, "
        "keeping small promises, telling the truth when it's easier not to.",
        "You can't control how fast others trust you. You can control whether you keep making "
        "deposits.",
    ), "What is one small promise you can keep this week?"),
    R('boundaries', 'Boundaries are care', 'relationships', (
        "Saying no to a party, leaving early, not answering a certain number: these can feel rude "
        "or dramatic. They're not. They're how you protect something precious.",
        "People who support your recovery will understand, even if it takes them a moment. People "
        "who push back are showing you something important too.",
        "A boundary isn't a wall to keep everyone out. It's a gate you decide when to open.",
    ), "Where in your life do you need a clearer boundary?"),
    R('finding-your-people', 'Finding your people', 'relationships', (
        "Isolation is one of the easiest ways back to old habits. Connection is one of the "
        "strongest protections we have.",
        "Your people might be in a meeting room, an online group, a gym, a church, a class or this "
        "community. What matters is that they know your story and want good things for you.",
        "It can take a few tries to find them. Keep looking. They're looking for you too.",
    ), "Who in your life makes you feel more like yourself?"),
    R('making-amends', 'Making things right', 'relationships', (
        "Most of us left some damage behind. Facing it can feel overwhelming, so it's tempting to "
        "either ignore it or try to fix everything at once.",
        "Repair works best when it's thoughtful. Sometimes that means a sincere apology. Sometimes "
        "it means paying something back. Sometimes the best amends is simply living differently.",
        "Talk it through with someone you trust first. The goal is repair, not relief at someone "
        "else's expense.",
    ), "Is there a relationship you'd like to begin repairing?"),

    # --- Self-compassion --------------------------------------------------
    R('talk-to-yourself-kindly', 'Talk to yourself like a friend', 'self-compassion', (
        "Listen to the voice in your head after a mistake. Would you ever speak that way to "
        "someone you love?",
        "Harshness feels like motivation, but it usually leads to hiding and giving up. Kindness "
        "is what makes it possible to try again.",
        "Next time you stumble, try saying what you'd say to a friend: \"That was hard. You're "
        "learning. Let's figure out the next step.\"",
    ), "What would a good friend say to you today?"),
    R('progress-not-perfection', 'Progress, not perfection', 'self-compassion', (
        "Recovery doesn't follow a straight line. Some weeks feel strong; some feel like you're "
        "barely holding on. Both are part of it.",
        "Measuring yourself against a perfect version of recovery will always leave you short. "
        "Measure against where you were instead.",
        "If you're more honest, more connected or more present than you were before, you're "
        "making progress, even on the hard days.",
    ), "How are you different now from when you started?"),
    R('rest-is-recovery', 'Rest is part of the work', 'self-compassion', (
        "There's a lot to rebuild, and it's tempting to fill every hour with self-improvement. "
        "But an exhausted mind is a vulnerable one.",
        "Sleep, quiet, a slow afternoon: these aren't laziness. They're how your nervous system "
        "settles after a long time on high alert.",
        "Giving yourself permission to rest is a recovery skill, not a break from recovery.",
    ), "What kind of rest does your body need today?"),
    R('you-are-not-your-past', 'More than your worst moments', 'self-compassion', (
        "It's easy to define yourself by the worst things you did while using. Those moments are "
        "part of your story, but they're not the whole story.",
        "Every day in recovery adds new chapters: the honest conversation, the craving you rode "
        "out, the morning you showed up when you didn't want to.",
        "You're allowed to be someone who made mistakes and someone who is changing. Both are "
        "true.",
    ), "What is something you've done in recovery that you're proud of?"),

    # --- Purpose & values -------------------------------------------------
    R('toward-not-away', 'Toward, not just away', 'purpose', (
        "Staying away from a substance is the start. Moving toward a life you care about is what "
        "keeps you there.",
        "Think about what you want more of: closeness, health, creativity, faith, adventure, "
        "calm. These are the things recovery makes room for.",
        "When the reason is only \"don't,\" it wears thin. When the reason is \"I want this life,\" "
        "it grows.",
    ), "What do you want more of in your life?"),
    R('small-wins', 'Count the small wins', 'purpose', (
        "Big milestones are worth celebrating, but they're far apart. In between, it helps to "
        "notice the small things.",
        "Paying a bill on time. Cooking dinner. Answering a call you'd have avoided. Making it "
        "through a hard evening. Each one is evidence that you're building something.",
        "Write them down. On difficult days, the list will remind you how far you've come.",
    ), "What are three small wins from this week?"),
    R('helping-others', 'Helping someone else', 'purpose', (
        "One of the surprising gifts of recovery is that your experience can help someone else. "
        "The hardest parts of your story might be exactly what another person needs to hear.",
        "You don't need to be an expert. A kind comment, a phone call, sharing what worked for "
        "you: these matter more than you know.",
        "Helping others also keeps your own recovery close. It's hard to forget where you came "
        "from while offering a hand to someone who's still there.",
    ), "Who could use a word of encouragement from you?"),
    R('one-step', 'The next right step', 'purpose', (
        "When life feels overwhelming, it's tempting to try to solve everything at once. That "
        "usually leads to paralysis.",
        "Instead, ask a simpler question: what is the next right thing? Not the whole plan, just "
        "the next step. Make the call. Eat the meal. Go to bed.",
        "A day made of next right steps is usually a good day, even if it never felt like one.",
    ), "What is your next right step today?"),

    # --- Gratitude & joy --------------------------------------------------
    R('gratitude-practice', 'Looking for the good', 'gratitude', (
        "Gratitude isn't pretending everything is fine. It's training your attention to notice "
        "what is going right alongside what is hard.",
        "A brain used to scanning for threats needs practice to spot good things. Three small "
        "ones a day is enough: a warm drink, a kind text, a moment of quiet.",
        "Over time, the habit changes what you see first.",
    ), "What are three things you're grateful for right now?"),
    R('sober-fun', 'Fun is allowed', 'gratitude', (
        "Many people worry that life in recovery will be dull. It doesn't have to be. Joy is not "
        "only allowed; it's protective.",
        "Laughter, music, games, nature, movement, creating something: these give your brain "
        "rewards that don't cost you anything the next morning.",
        "If you've forgotten what you enjoy, treat it like an experiment. Try things and notice "
        "what lights you up.",
    ), "What made you laugh or smile recently?"),
    R('present-moment', 'Being here for it', 'gratitude', (
        "Using often meant missing things: conversations you don't remember, events you barely "
        "attended, days that blurred together.",
        "Recovery gives you your presence back. You get to taste your food, hear the whole story, "
        "and remember the evening.",
        "Pause a few times today and notice where you are. Being here for your own life is one of "
        "the quiet rewards.",
    ), "What moment today do you want to remember?"),

    # --- Setbacks & resilience --------------------------------------------
    R('after-a-slip', 'After a slip', 'resilience', (
        "A slip can bring a flood of shame and the thought, \"I've ruined everything, so why "
        "stop now?\" That thought is the most dangerous part of a slip.",
        "A slip is an event, not an identity. Everything you learned is still there. Your "
        "relationships, your skills and your reasons are still there.",
        "Reach out quickly. Be honest. Look at what led up to it, then take the next step. "
        "Recovery is not erased by one bad day.",
    ), "What would you want to tell yourself the morning after a slip?"),
    R('hard-days-pass', 'Hard days end too', 'resilience', (
        "Some days are just hard. Nothing goes right, everything feels heavy, and the old "
        "escape looks tempting.",
        "On those days, lower the bar. The goal isn't to have a good day; it's to get through "
        "this one without making it worse. Eat something. Talk to someone. Go to bed early.",
        "Tomorrow is a new day, and it often feels very different from this one.",
    ), "What is your plan for the next hard day?"),
    R('ask-what-not-why', 'Ask what, not why', 'resilience', (
        "\"Why do I keep doing this?\" can turn into an endless loop of self-blame. It rarely "
        "leads anywhere useful.",
        "\"What happened?\" is more helpful. What came before, what was I feeling, what did I need, "
        "what could I try next time? \"What\" questions lead to plans.",
        "Curiosity is kinder than judgment, and far more useful.",
    ), "What is one situation you could get curious about instead of critical?"),
]

REFLECTIONS_BY_SLUG = {r.slug: r for r in REFLECTIONS}

# How many days back the "recent" list on the hub reaches.
RECENT_DAYS = 7


def get_reflection(slug):
    return REFLECTIONS_BY_SLUG.get(slug)


def reflection_for_date(day):
    """Deterministic pick for a date: everyone sees the same one that day."""
    return REFLECTIONS[day.toordinal() % len(REFLECTIONS)]


def todays_reflection():
    """Today's reading, by the member's local date."""
    return reflection_for_date(timezone.localdate())


def by_theme():
    """[(theme_key, theme_label, [reflections])] in THEMES order."""
    return [(key, label, [r for r in REFLECTIONS if r.theme == key])
            for key, label in THEMES.items()]
