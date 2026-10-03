"""Guided day-by-day recovery programs.

A program is a sequence of short daily lessons. Each lesson takes about
3-5 minutes to read, has one concrete action that links to an existing part
of the site (a worksheet, the relapse plan, a check-in, Craving SOS,
meetings, groups, Anchor), and ends with a journal prompt.

Pacing: one lesson per day. Day 1 opens when you enroll. Each later day
opens once the previous day is complete and that completion was on an
earlier local date. Missed days don't count against you; you pick up
where you left off.

Access (see program_views.py): the first `free_days` lessons of each program
are free (FREE_DAYS unless the program sets its own). Later lessons are
Premium. Lessons a member has already completed stay readable if their
Premium lapses.

Kinds: the one 'core' program (First 30 Days) is for anyone. 'track'
programs are shorter, substance-specific companions; they live one per
file in resources/program_tracks/.

All lesson text is original to MyRecoveryPal and works for any path to
recovery. It never gives medical advice; anything touching withdrawal or
medication points to a doctor.
"""
from .program_types import FREE_DAYS, A, Action, L, Lesson, Program  # noqa: F401

FIRST_30_DAYS = Program(
    slug='first-30-days',
    title='First 30 Days',
    icon='🌱',
    summary='A gentle, practical guide through your first month: one short lesson and one small action a day.',
    intro=(
        'The first month is when recovery asks the most of you and gives back the least, at '
        'least at first. This program breaks it into thirty small steps. Each day takes about '
        'five minutes to read and has one thing to do. You don\'t need to be perfect at any of '
        'it. You just need to come back tomorrow.'
    ),
    audience='Anyone in their first weeks of recovery from alcohol, drugs, gambling or another addiction, or anyone starting again.',
    meta_description=(
        'A free 30-day recovery program: one five-minute lesson and one small action a day '
        'for your first month sober. For any path to recovery.'
    ),
    weeks=(
        'Week 1: Getting through today',
        'Week 2: Body and mind',
        'Week 3: People',
        'Week 4: Building a life',
        'Days 29-30: Looking ahead',
    ),
    lessons=(
        # --- Week 1: Getting through today --------------------------------
        L('You started', [
            "Whatever brought you here, today counts. Starting is the hardest part, and many people "
            "start more than once before it sticks. That's not failure; it's how change usually works.",
            "For the next thirty days, you only have one job each day: read a short lesson and do one "
            "small thing. Some days will feel easy. Some won't. Both count.",
            "Today's action is the simplest one in the program: mark the start. Setting your sobriety "
            "date gives you a counter to watch grow and a date to be proud of later.",
        ], A('Set your sobriety date', 'accounts:edit_profile',
             detail='Add your start date in your profile. You can keep it private.'),
            "What made you decide to start now?"),
        L('Your reason', [
            "On hard days, willpower runs out. Reasons last longer. Most people in long-term "
            "recovery can tell you exactly why they stopped, and they remind themselves often.",
            "Your reason doesn't have to be noble. \"I'm tired of waking up like this\" is a "
            "perfectly good reason. So is a person, a job, your health, or simply wanting to know "
            "who you are without it.",
            "Write it down where you'll see it. The daily pledge on your home screen can show your "
            "reason, and a photo if you like, every single morning.",
        ], A('Take today\'s pledge', 'accounts:progress',
             detail='Tap "I pledge to stay sober today" and add your reason.'),
            "If you could only keep one reason, which would it be?"),
        L('One day at a time, literally', [
            "Thinking about never using again can make today feel impossible. So don't think about "
            "never. Think about today.",
            "Getting through today is a real, achievable goal. Tomorrow you can make the same "
            "decision again. Long stretches of recovery are simply a lot of todays, stacked up.",
            "A quick check-in each day helps. It takes thirty seconds and builds a picture of your "
            "mood and cravings over time that you'll be glad to have later.",
        ], A('Do today\'s check-in', 'accounts:daily_checkin',
             detail='Rate your mood, cravings and energy. It takes under a minute.'),
            "What would make today 10% easier?"),
        L('Know your triggers', [
            "A trigger is anything that makes you want to use: a place, a person, a feeling, a time "
            "of day, even a song. Everyone has them, and they're not a sign of weakness.",
            "In the first month, the best defense is simply knowing where they are. You can't avoid "
            "every trigger, but you can stop being surprised by them.",
            "Today, map yours. It takes about fifteen minutes and you'll use what you learn for the "
            "rest of this program.",
        ], A('Fill in the Trigger Map', 'resources:worksheet_detail', ('trigger-map',),
             detail='Work through people, places, feelings and times.'),
            "Which trigger surprised you most when you wrote it down?"),
        L('When a craving hits', [
            "Cravings are one of the hardest parts of early recovery, and also one of the most "
            "misunderstood. They feel like they'll keep growing until you give in. They don't.",
            "A craving rises, peaks and falls, usually within twenty to thirty minutes. Your job is to "
            "get through the peak: breathe, move, change rooms, call someone, eat something.",
            "It helps to know where to go before you need it. Bookmark the Craving SOS page now, so "
            "it's one tap away when a wave comes.",
        ], A('Open Craving SOS', 'core:craving_sos',
             detail='Try the breathing exercise once now, while things are calm.'),
            "What has helped you get through a craving before, even a little?"),
        L('Make a plan for hard moments', [
            "In a moment of crisis, nobody thinks clearly. That's why pilots use checklists and why "
            "people in recovery write relapse prevention plans on calm days.",
            "Your plan is simple: your warning signs, what helps, who to call, and what to do if "
            "things go wrong. It's private, and you can change it any time.",
            "You'll come back to this plan often. Today, just get a first version down.",
        ], A('Start your relapse prevention plan', 'accounts:relapse_plan',
             detail='Fill in at least your support contacts and coping strategies.'),
            "What's the first warning sign that you're starting to struggle?"),
        L('You made it a week', [
            "Seven days. However they went, you're still here and still trying, and that matters "
            "more than how smooth it looked.",
            "Take a moment to notice what's different. Maybe you slept better one night. Maybe you "
            "had a conversation you'll actually remember. Maybe it was just hard, and you did it "
            "anyway.",
            "Recovery grows in connection. Today, say hello to the community. You don't have to "
            "share your story; a simple \"one week today\" is plenty.",
        ], A('Post in the community', 'accounts:social_feed',
             detail='Share a short update, or just like someone else\'s post.'),
            "What's one thing that went better this week than you expected?"),

        # --- Week 2: Body and mind ----------------------------------------
        L('Hungry, angry, lonely, tired', [
            "Many cravings are your body or mind asking for something simpler. Recovery groups have "
            "a shorthand for the four most common: hungry, angry, lonely, tired.",
            "When an urge shows up, check those four first. A meal, a phone call, saying what's "
            "bothering you, or an early night can take the edge off more than you'd expect.",
            "Make it a habit this week: whenever you notice a craving, run the four-question check "
            "before deciding what it means.",
        ], A('Add HALT notes to your plan', 'accounts:relapse_plan',
             detail='Fill in the HALT section: how each one shows up for you.'),
            "Which of the four catches you most often?"),
        L('Sleep is part of recovery', [
            "Sleep is often a mess in early recovery. It can take weeks for your body to find its "
            "rhythm again, and poor sleep makes cravings and moods harder to manage.",
            "You can help it along: the same wake-up time every day, screens off a little earlier, "
            "less caffeine after lunch, and a short wind-down routine.",
            "If sleep problems are severe or you're worried about withdrawal, talk to a doctor. It's "
            "a common, treatable part of early recovery.",
        ], A('Note your sleep in today\'s check-in', 'accounts:daily_checkin',
             detail='Use your energy rating, and jot how you slept in the notes.'),
            "What's one small change you could make to your evenings this week?"),
        L('Feed yourself', [
            "Using often crowds out regular meals. In early recovery, low blood sugar can feel a lot "
            "like a craving: shaky, irritable, restless.",
            "You don't need a perfect diet. Aim for three regular meals, something with protein, and "
            "plenty of water. Keep an easy snack with you for the late afternoon.",
            "Eating regularly is one of the simplest ways to make the hard hours easier.",
        ], None, "When during the day are you most likely to skip eating?"),
        L('Move a little', [
            "Movement is one of the best natural mood lifters there is. It burns off restless energy, "
            "helps sleep, and gives your brain some of the reward it's missing.",
            "It doesn't need to be a workout. A ten-minute walk counts. So does stretching, dancing in "
            "the kitchen, or taking the stairs.",
            "Try a short walk today, ideally outside. Notice how you feel before and after.",
        ], None, "How did you feel after moving today?"),
        L('Thoughts that lead to using', [
            "Between a trigger and a craving there's usually a thought: \"I deserve it,\" \"Just "
            "one won't hurt,\" \"What's the point?\" These thoughts feel true in the moment.",
            "Catching and questioning them is one of the most effective skills in recovery. It's "
            "the heart of cognitive behavioral therapy, and you can practice it on paper.",
            "Today, take one recent difficult moment and walk it through the ABC Thought Record.",
        ], A('Try the ABC Thought Record', 'resources:worksheet_detail', ('abc-thought-record',),
             detail='Pick one moment from the past few days.'),
            "What thought most often shows up right before a craving?"),
        L('Riding the wave', [
            "This week you've probably had at least one strong craving. Each one you get through "
            "without using teaches your brain that urges pass on their own.",
            "Logging cravings turns them into information: when they hit, what sets them off, and "
            "what actually works for you. Patterns usually show up within a week or two.",
            "Next time a craving comes, log it as soon as it passes.",
        ], A('Open the Urge Log', 'resources:worksheet_detail', ('urge-log',),
             detail='Log your most recent craving, or keep it ready for the next one.'),
            "What did your last craving teach you?"),
        L('Big feelings', [
            "Without something to numb them, feelings can arrive at full volume: anger, sadness, "
            "guilt, even sudden joy. That's normal, and it means you're feeling your life again.",
            "Feelings are information, not instructions. Name the feeling, notice where it sits in "
            "your body, and give it time. Most feelings shift within minutes if you let them.",
            "If a feeling is overwhelming, talk to someone. Anchor, the AI coach, is available any "
            "time if no one else is around.",
        ], A('Talk it through with Anchor', 'accounts:recovery_coach',
             detail='Tell Anchor what you\'re feeling today.'),
            "What feeling has been loudest this week?"),

        # --- Week 3: People -----------------------------------------------
        L('Two weeks', [
            "Fourteen days. Your body and brain are already recalibrating, even if it doesn't feel "
            "like it yet.",
            "This week is about people: the ones who help, the ones who don't, and the ones you "
            "haven't met yet. Recovery is much harder alone, and much more possible together.",
            "Take a minute to look back at your check-ins so far. Patterns in mood and cravings "
            "often start to show by now.",
        ], A('Look at your progress', 'accounts:progress',
             detail='Look at your streak and your mood and craving trends.'),
            "Who has helped you most in the last two weeks?"),
        L('Find a meeting', [
            "Meetings, whether 12-step, SMART Recovery, Refuge, secular or faith-based, are one of "
            "the most reliable sources of support in recovery. They're free, and many are online.",
            "You don't have to speak. You don't have to believe anything. You can just listen. Many "
            "people try a few different meetings before one feels right.",
            "Today, find one meeting you could attend this week.",
        ], A('Browse meetings', 'support_services:meeting_list',
             detail='Filter by online or in person, and pick one to try.'),
            "What would make it easier for you to try a meeting?"),
        L('Being honest', [
            "Addiction usually needs secrets to survive. Recovery thrives on honesty, starting with "
            "being honest with yourself.",
            "That doesn't mean telling everyone everything. It means having at least one person who "
            "knows what's really going on with you.",
            "Think about who that person could be: a friend, a family member, a sponsor, a "
            "counselor, someone from a group.",
        ], None, "Who is one person you could be completely honest with?"),
        L('Saying no', [
            "Sooner or later someone will offer you a drink, invite you somewhere risky, or ask why "
            "you're not using. Having your answer ready makes it much easier.",
            "You don't owe anyone an explanation. \"No thanks, I'm good\" is complete. So is "
            "\"I'm not drinking right now\" or simply leaving early.",
            "Practice it out loud today. It sounds silly, and it works.",
        ], None, "What's your go-to line for saying no?"),
        L('Boundaries', [
            "Some people and places will need to change, at least for now. That might mean not "
            "answering certain numbers, skipping certain events, or limiting time with people who "
            "still use.",
            "Boundaries aren't punishments. They're how you protect something precious while it's "
            "still fragile.",
            "Look back at your Trigger Map. Which people or places need a clearer boundary?",
        ], A('Review your Trigger Map', 'resources:worksheet_detail', ('trigger-map',),
             detail='Add a plan for your highest-risk people and places.'),
            "Where in your life do you need a clearer boundary?"),
        L('Let someone in your corner', [
            "The people who love you often want to help but don't know how. Letting them see your "
            "progress gives them a way in.",
            "MyRecoveryPal lets you invite a supporter: a partner, parent or friend who can follow "
            "your milestones and get a gentle nudge if you go quiet.",
            "If that feels like too much right now, simply telling one person how you're doing "
            "counts too.",
        ], A('Invite a supporter', 'accounts:supporter_invite',
             detail='Choose someone who wants good things for you.'),
            "Who would you want cheering for you?"),
        L('Find your people', [
            "Three weeks in, you've earned a place in a community of people who understand. Groups "
            "on MyRecoveryPal gather around recovery stage, substance, location and interests.",
            "Joining a group gives you a smaller, more personal circle than the main feed, where "
            "people get to know your name and your story.",
            "Find one group that fits and join it today.",
        ], A('Browse groups', 'accounts:groups_list',
             detail='Join one group and say hello.'),
            "What would you most like from a recovery community?"),

        # --- Week 4: Building a life --------------------------------------
        L('Toward, not just away', [
            "So far, much of this program has been about staying away from using. This week is about "
            "what you're moving toward.",
            "Your values are what you want your life to stand for: family, honesty, health, "
            "creativity, faith, freedom. Recovery lasts when it serves something you care about.",
            "Today, name yours.",
        ], A('Fill in the Values Compass', 'resources:worksheet_detail', ('values-compass',),
             detail='Name your top five values and one action for this week.'),
            "What do you want your life to be about a year from now?"),
        L('Fill the empty hours', [
            "When using stops, it leaves gaps: evenings, weekends, the drive home. Empty time is "
            "where old habits wait.",
            "Look at your riskiest hours and plan something specific for them: a walk, a meeting, a "
            "call, cooking, a class, a show you save for that time.",
            "New routines feel awkward at first. Repetition makes them yours.",
        ], None, "Which hour of the week feels emptiest, and what will you put there?"),
        L('Fun is allowed', [
            "Many people worry that sober life will be dull. It doesn't have to be, and finding joy "
            "is protective, not optional.",
            "Your brain is relearning how to enjoy ordinary things. Help it along: try something new, "
            "go back to something you used to love, or do something just because it's fun.",
            "Plan one fun thing for this week.",
        ], None, "What's something you used to enjoy that you'd like to try again?"),
        L('Take stock of your life', [
            "Recovery touches everything: health, relationships, work, money, fun, meaning. Some "
            "areas are probably already improving. Some may need attention.",
            "A quick balance check shows you where to put your energy next, and gives you something "
            "to compare against in a few months.",
        ], A('Fill in the Lifestyle Balance Wheel', 'resources:worksheet_detail', ('lifestyle-balance-wheel',),
             detail='Rate eight areas and pick one to improve.'),
            "Which area of your life has improved most since you started?"),
        L('Money and recovery', [
            "Addiction is expensive. Many people are surprised how much they've saved after a few "
            "weeks, and how much stress came from money problems.",
            "Take an honest look today. What were you spending? What could that money do instead? "
            "Even small steps, like setting up a savings goal, can be motivating.",
            "If debt or money problems feel overwhelming, free non-profit credit counseling services "
            "can help you make a plan.",
        ], None, "What would you like to do with the money you're no longer spending?"),
        L('If you slip', [
            "Nobody plans to slip, but planning for the possibility is one of the smartest things "
            "you can do. A slip doesn't erase your progress, but the shame afterwards can.",
            "If it happens: reach out quickly, be honest, look at what led up to it, and take the "
            "next step. One bad day is not the end of recovery.",
            "Today, read through the emergency steps in your relapse prevention plan and make sure "
            "they're up to date.",
        ], A('Update your emergency steps', 'accounts:relapse_plan',
             detail='Check the "If a slip happens" section.'),
            "What would you want to say to yourself the morning after a slip?"),
        L('Gratitude', [
            "Gratitude isn't pretending everything is fine. It's training your attention to notice "
            "what's going right alongside what's hard.",
            "Four weeks in, there's probably more to be grateful for than you'd have guessed on Day 1.",
            "End today with a short nightly review: what went well, where you'd do better, and three "
            "things you're grateful for.",
        ], A('Do a Nightly Review', 'resources:worksheet_detail', ('nightly-review',),
             detail='A five-minute look back at your day.'),
            "What are three things you're grateful for today?"),

        # --- Days 29-30: Looking ahead ------------------------------------
        L('Look how far you\'ve come', [
            "Twenty-nine days ago you started this program. Look back at what you've built: a "
            "trigger map, a relapse prevention plan, a set of values, people in your corner, and a "
            "month of check-ins.",
            "Notice the changes, big and small. Recovery is often easier to see looking back than "
            "looking forward.",
            "Record this milestone. You earned it.",
        ], A('Add a milestone', 'accounts:add_milestone',
             detail='Record your first month, or any win that matters to you.'),
            "How are you different now from when you started?"),
        L('Day 30, and what comes next', [
            "Thirty days. That's a real achievement, and it's worth celebrating.",
            "The work doesn't stop here, but you now have tools you didn't have a month ago: a plan, "
            "people, routines, and the knowledge that cravings pass and hard days end.",
            "Keep going with the habits that worked: daily check-ins, meetings, your community and "
            "the daily reflections. Then come back to these lessons any time you need them.",
        ], A('Read today\'s reflection', 'resources:reflections',
             detail='A short daily reading to keep the momentum going.'),
            "What are your intentions for the next thirty days?"),
    ),
)

from .program_tracks import TRACKS  # noqa: E402

PROGRAMS = [FIRST_30_DAYS, *TRACKS]
PROGRAMS_BY_SLUG = {p.slug: p for p in PROGRAMS}
CORE_PROGRAMS = [p for p in PROGRAMS if p.kind == 'core']
TRACK_PROGRAMS = [p for p in PROGRAMS if p.kind == 'track']


def get_program(slug):
    return PROGRAMS_BY_SLUG.get(slug)
