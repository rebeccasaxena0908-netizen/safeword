"""
Hand-written seed corpus.

Each entry is one realistic message plus its gold labels. These are the
ground truth everything else is derived from - the expansion script only
paraphrases, it never invents new label combinations.

Fields: text, intent, role, distress, scope, targets, hard_negative, lang

Target is ~400 seeds. This file ships ~130 covering the full label space.
Extend it by adding calls to add() below; SCHEMA.md defines every label and
the composition targets you are aiming for.
"""

S = []


def add(text, intent, role, distress, scope="all", targets=None,
        hard_negative=False, lang="en", furniture=None):
    S.append({
        "text": text, "intent": intent, "role": role, "distress": distress,
        "scope": scope, "targets": targets or [], "hard_negative": hard_negative,
        "lang": lang, "furniture": furniture,
    })


# ---------------------------------------------------------------------------
# stolen_confirmed / owner - the core emergency class, all three registers
# ---------------------------------------------------------------------------
add("someone just snatched my phone at the metro station, lock everything now", "stolen_confirmed", "owner", "panic")
add("OMG my phone got stolen!! please lock all my accounts RIGHT NOW", "stolen_confirmed", "owner", "panic")
add("my phone was stolen ten minutes back near connaught place. i need everything locked", "stolen_confirmed", "owner", "worried")
add("phone stolen. lock it all. please hurry", "stolen_confirmed", "owner", "panic")
add("A man on a bike grabbed my phone while I was walking. Please initiate the lockdown.", "stolen_confirmed", "owner", "calm")
add("i got mugged, they took my phone and it was unlocked, do everything", "stolen_confirmed", "owner", "panic")
add("someone pickpocketed me on the bus and my phone is gone, it was open", "stolen_confirmed", "owner", "worried")
add("My phone has been stolen. Kindly proceed with securing my accounts.", "stolen_confirmed", "owner", "calm")
add("theft!! phone gone!! everything locked please!!!", "stolen_confirmed", "owner", "panic")
add("guy snatched my phone outside the station and ran, im using my friends laptop", "stolen_confirmed", "owner", "worried")
add("robbed at knifepoint, phone taken, screen was unlocked. lock everything immediately", "stolen_confirmed", "owner", "panic")
add("they took my bag with my phone in it, phone was not locked", "stolen_confirmed", "owner", "worried")
add("someone stole my phone from the table while i was ordering coffee", "stolen_confirmed", "owner", "worried")
add("my phone got snatched in the market just now please help", "stolen_confirmed", "owner", "panic")
add("Phone stolen from my desk at work. It was unlocked. Please lock my accounts.", "stolen_confirmed", "owner", "calm")

# code-mixed
add("bhai mera phone chori ho gaya, sab kuch band kar do jaldi", "stolen_confirmed", "owner", "panic", lang="hi-en")
add("mera phone metro me chori ho gaya hai, please sab accounts lock karo", "stolen_confirmed", "owner", "worried", lang="hi-en")
add("phone chori ho gaya!! turant sab band karo!!", "stolen_confirmed", "owner", "panic", lang="hi-en")
add("koi mera phone le gaya, unlocked tha, sab lock kar do", "stolen_confirmed", "owner", "panic", lang="hi-en")
add("emergency hai, phone snatch ho gaya, sab accounts freeze karo", "stolen_confirmed", "owner", "panic", lang="hi-en")

# ---------------------------------------------------------------------------
# stolen_confirmed with explicit scope - the SCOPE=except / especially pair
# ---------------------------------------------------------------------------
add("my phone was stolen, lock everything except my email", "stolen_confirmed", "owner", "worried", "except", ["gmail"])
add("phone stolen! lock everything, especially my email", "stolen_confirmed", "owner", "panic", "all", ["gmail"])
add("someone took my phone. lock it all apart from my bank, i need to check something", "stolen_confirmed", "owner", "worried", "except", ["demobank"])
add("stolen phone, lock everything but not whatsapp, my family needs to reach me", "stolen_confirmed", "owner", "worried", "except", ["whatsapp"])
add("my phone is gone, freeze everything and above all the bank account", "stolen_confirmed", "owner", "panic", "all", ["demobank"])
add("theft. lock all my accounts other than telegram.", "stolen_confirmed", "owner", "calm", "except", ["telegram"])
add("phone snatched, do everything except gmail for now", "stolen_confirmed", "owner", "worried", "except", ["gmail"])
add("someone stole my phone, lock everything and make sure you get instagram", "stolen_confirmed", "owner", "panic", "all", ["instagram"])
add("stolen! only lock my bank account, nothing else for now", "stolen_confirmed", "owner", "worried", "only", ["demobank"])
add("my phone got taken, just instagram and telegram and nothing else", "stolen_confirmed", "owner", "worried", "only", ["instagram", "telegram"])
add("phone stolen, lock only the bank please", "stolen_confirmed", "owner", "panic", "only", ["demobank"])
add("lock everything apart from my email and whatsapp, phone was stolen", "stolen_confirmed", "owner", "worried", "except", ["gmail", "whatsapp"])

# ---------------------------------------------------------------------------
# lost_uncertain - no adversary asserted
# ---------------------------------------------------------------------------
add("i lost my phone somewhere, not sure where", "lost_uncertain", "owner", "calm")
add("cant find my phone anywhere, i think i left it in the auto", "lost_uncertain", "owner", "worried")
add("I seem to have misplaced my phone. Could you sign me out of my devices?", "lost_uncertain", "owner", "calm")
add("my phone is missing since morning, might have dropped it", "lost_uncertain", "owner", "worried")
add("lost my phone at the party last night, no idea where", "lost_uncertain", "owner", "calm")
add("phone kho gaya hai, pata nahi kahan", "lost_uncertain", "owner", "calm", lang="hi-en")
add("i left my phone in the cab and the driver isnt picking up", "lost_uncertain", "owner", "worried")
add("Can't locate my phone. Probably at home but I want to be safe.", "lost_uncertain", "owner", "calm")
add("phone missing, checked everywhere, starting to worry", "lost_uncertain", "owner", "worried")
add("misplaced my phone at the gym, going back to look but sign me out just in case", "lost_uncertain", "owner", "calm")
add("mera phone kho gaya, ghar pe hi hoga shayad par safe rehna hai", "lost_uncertain", "owner", "calm", lang="hi-en")
add("i dont know where my phone is, last saw it at lunch", "lost_uncertain", "owner", "worried")

# ---------------------------------------------------------------------------
# proxy - a third party reporting on the owner's behalf
# ---------------------------------------------------------------------------
add("Hi, this is Rebecca's friend. Her phone just got snatched and she asked me to email you.", "stolen_confirmed", "proxy", "worried")
add("im mailing on behalf of my sister, someone stole her phone at the station", "stolen_confirmed", "proxy", "worried")
add("Rebecca asked me to contact you - her phone was stolen about 15 minutes ago", "stolen_confirmed", "proxy", "calm")
add("hey this is her colleague, she got robbed and cant access anything, please lock her accounts", "stolen_confirmed", "proxy", "panic")
add("my friend lost her phone and asked me to write to you from my account", "lost_uncertain", "proxy", "calm")
add("This is her brother. Phone stolen near the metro. She wants everything locked.", "stolen_confirmed", "proxy", "worried")
add("didi ka phone chori ho gaya, unhone bola aapko mail karne ke liye", "stolen_confirmed", "proxy", "worried", lang="hi-en")
add("she asked me to mail you, her phone got snatched and she is with the police right now", "stolen_confirmed", "proxy", "worried")
add("hi im writing for a friend whose phone was just stolen, she gave me this address", "stolen_confirmed", "proxy", "worried")
add("On behalf of Rebecca Saxena - device stolen, requesting account lockdown.", "stolen_confirmed", "proxy", "calm")
add("her phone got taken and she is really panicking, please do whatever you can", "stolen_confirmed", "proxy", "panic")
add("this is her roommate. she thinks she lost her phone on the bus.", "lost_uncertain", "proxy", "calm")

# ---------------------------------------------------------------------------
# mere_mention - theft discussed, no action requested. THE HARD NEGATIVES.
# ---------------------------------------------------------------------------
add("my friend's phone got stolen last week, so annoying for her", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("did you hear about the phone snatching gang in south delhi", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("i was reading an article about phone theft and account takeovers, scary stuff", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("someone stole my bicycle from outside the building", "out_of_scope", "mere_mention", "worried", hard_negative=True)
add("my cousin lost her phone in goa and had such a hard time getting back into her email", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("remember when my phone was stolen in 2022, worst week ever", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("there was a theft in our office yesterday, someone took a laptop", "out_of_scope", "mere_mention", "worried", hard_negative=True)
add("i lost my phone charger again, third one this month", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("if my phone ever gets stolen i honestly dont know what id do", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("watching a movie where the guy gets his phone stolen and everything falls apart", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("bhai uska phone chori ho gaya tha pichle mahine, bohot problem hui", "out_of_scope", "mere_mention", "calm", hard_negative=True, lang="hi-en")
add("my dad keeps losing his phone in the house, happens every single day", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("the news said phone thefts went up 30 percent this year", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("i lost my wallet not my phone, the phone is fine", "out_of_scope", "mere_mention", "worried", hard_negative=True)
add("she was telling me how her instagram got hacked after her phone was taken", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("writing a college project about phone theft and digital identity", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("my phone screen is broken, not stolen, just cracked", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("someone tried to steal my phone but i grabbed it back in time", "out_of_scope", "mere_mention", "worried", hard_negative=True)
add("that guy in the news got his bank emptied after losing his phone", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("i keep my phone locked always after what happened to my friend", "out_of_scope", "mere_mention", "calm", hard_negative=True)

# ---------------------------------------------------------------------------
# out_of_scope - ordinary mail that must never trigger anything
# ---------------------------------------------------------------------------
add("hey are we still on for dinner tomorrow", "out_of_scope", "owner", "calm", hard_negative=True)
add("Your monthly account statement is now available for download.", "out_of_scope", "owner", "calm", hard_negative=True)
add("Security newsletter: 5 ways to protect your accounts this year", "out_of_scope", "owner", "calm", hard_negative=True)
add("Unusual sign-in attempt detected on your account. Click here to verify.", "out_of_scope", "owner", "worried", hard_negative=True)
add("can you send me the notes from today's lecture", "out_of_scope", "owner", "calm", hard_negative=True)
add("Reminder: your electricity bill is due on the 15th", "out_of_scope", "owner", "calm", hard_negative=True)
add("Congratulations! You have won a prize. Claim now to unlock your reward.", "out_of_scope", "owner", "calm", hard_negative=True)
add("thanks for lunch today, was good catching up", "out_of_scope", "owner", "calm", hard_negative=True)
add("please freeze the project timeline, we need more time", "out_of_scope", "owner", "calm", hard_negative=True)
add("i need to lock in the venue for the event by friday", "out_of_scope", "owner", "calm", hard_negative=True)
add("logging out for the day, see you tomorrow", "out_of_scope", "owner", "calm", hard_negative=True)
add("my instagram password expired and i had to reset it", "out_of_scope", "owner", "calm", hard_negative=True)

# ---------------------------------------------------------------------------
# cancel_false_alarm - cancellation always wins
# ---------------------------------------------------------------------------
add("false alarm! found my phone, it was in my bag the whole time", "cancel_false_alarm", "owner", "calm")
add("stop stop, i found it. dont lock anything", "cancel_false_alarm", "owner", "worried")
add("nevermind, got my phone back from the shop where i left it", "cancel_false_alarm", "owner", "calm")
add("cancel the lockdown please, it was a mistake", "cancel_false_alarm", "owner", "calm")
add("phone mil gaya, sab cancel kar do", "cancel_false_alarm", "owner", "calm", lang="hi-en")
add("undo everything, my brother had taken my phone", "cancel_false_alarm", "owner", "calm")
add("Please disregard my previous email. The phone has been recovered.", "cancel_false_alarm", "owner", "calm")
add("dont lock my accounts, false alarm, everything is fine", "cancel_false_alarm", "owner", "calm")
add("wait no, i found it, please reverse whatever you did", "cancel_false_alarm", "owner", "worried")
add("my phone was stolen but actually no it wasnt, my friend was holding it. cancel.", "cancel_false_alarm", "owner", "calm")
add("false alarm, cancel it all", "cancel_false_alarm", "owner", "calm")
add("it turned up, no need to do anything", "cancel_false_alarm", "owner", "calm")

# ---------------------------------------------------------------------------
# partial_lockdown - bounded request, no emergency framing
# ---------------------------------------------------------------------------
add("can you log me out of instagram on all devices please", "partial_lockdown", "owner", "calm", "only", ["instagram"])
add("just sign me out of telegram everywhere, i used a public computer", "partial_lockdown", "owner", "calm", "only", ["telegram"])
add("please rotate my whatsapp password, i think i typed it somewhere odd", "partial_lockdown", "owner", "worried", "only", ["whatsapp"])
add("log me out of the bank, i left it open on a shared laptop", "partial_lockdown", "owner", "worried", "only", ["demobank"])
add("sign out all sessions on gmail please, routine cleanup", "partial_lockdown", "owner", "calm", "only", ["gmail"])
add("instagram se logout kar do sab jagah se", "partial_lockdown", "owner", "calm", "only", ["instagram"], lang="hi-en")

# ---------------------------------------------------------------------------
# status_query
# ---------------------------------------------------------------------------
add("did the lockdown go through?", "status_query", "owner", "worried")
add("what happened with my request, is my bank frozen", "status_query", "owner", "worried")
add("Could you confirm which accounts were secured?", "status_query", "owner", "calm")
add("is it done? did you lock everything", "status_query", "owner", "panic")
add("update me on the status please", "status_query", "owner", "calm")
add("kya hua, sab lock ho gaya?", "status_query", "owner", "worried", lang="hi-en")

# ---------------------------------------------------------------------------
# verification_response - answers to challenge questions
# ---------------------------------------------------------------------------
add("bruno, my nani's dog", "verification_response", "owner", "calm")
add("the dog was called Bruno", "verification_response", "owner", "calm")
add("Bruno!!", "verification_response", "owner", "panic")
add("i think it was bruno? my grandmothers dog yes bruno", "verification_response", "owner", "worried")
add("ghaziabad, thats where i opened the account", "verification_response", "owner", "calm")
add("St Marys Convent, thats my first school", "verification_response", "owner", "calm")
add("it was ghaziabad i think", "verification_response", "owner", "worried")

# ---------------------------------------------------------------------------
# Messages carrying email furniture - signatures, quoted replies, forwards.
# The 'text' here is the RAW body; the cleaner must strip everything but the
# first block.  furniture marks what M0 has to remove.
# ---------------------------------------------------------------------------
add("""my phone was stolen at the metro, lock everything

--
Sent from my iPhone""", "stolen_confirmed", "owner", "worried", furniture="signature")

add("""someone snatched my phone, please lock my accounts now

Best regards,
Rebecca Saxena
Senior Analyst, HDFC Bank
+91 98765 43210""", "stolen_confirmed", "owner", "worried", furniture="signature")

add("""phone stolen! do everything!

> On Tue, 12 Aug 2025, Rebecca wrote:
> hey are we meeting at 6 today
> let me know""", "stolen_confirmed", "owner", "panic", furniture="quoted_reply")

add("""forwarding this, her phone got taken

---------- Forwarded message ----------
From: Rebecca Saxena <rebecca@example.com>
Date: Tue, 12 Aug 2025
Subject: help

someone took my phone please help""", "stolen_confirmed", "proxy", "worried", furniture="forwarded_header")

add("""i lost my phone somewhere in the office today

Regards,
Rebecca

This email and any attachments are confidential and intended solely for the
addressee. If you are not the intended recipient please delete it.""",
    "lost_uncertain", "owner", "calm", furniture="signature+disclaimer")

add("""false alarm, found it

Sent from my Galaxy""", "cancel_false_alarm", "owner", "calm", furniture="signature")

add("""my friend's phone got stolen last week

--
Rebecca Saxena
Sent from Outlook for iOS""", "out_of_scope", "mere_mention", "calm", hard_negative=True, furniture="signature")


# ---------------------------------------------------------------------------
# Adversarial imposter set - HELD OUT ENTIRELY from train/dev/test of the
# intent models.  Used only to evaluate stylometry (M4b).  These are what an
# attacker sitting in a compromised Emergency Account would plausibly write:
# correct sender, correct intent, wrong author.
# ---------------------------------------------------------------------------
IMPOSTERS = [
    "Dear Sir/Madam, I hereby request the immediate initiation of the account lockdown protocol for this user.",
    "Please execute a full security lockdown on all associated accounts at your earliest convenience.",
    "This is to inform you that the device has been compromised. Kindly proceed with credential rotation.",
    "I am writing to request urgent deactivation of all active sessions associated with this account.",
    "Requesting immediate suspension of banking access due to a reported device theft incident.",
    "Kindly initiate the emergency protocol. The subject's phone is no longer in their possession.",
    "Attention: security incident reported. Please action full lockdown including email credentials.",
    "Good evening. I would like to report a stolen device and request comprehensive account protection.",
    "As per protocol, I am notifying you of a theft event requiring immediate remedial action.",
    "Please be advised that immediate password rotation across all platforms is required.",
]

# ---------------------------------------------------------------------------
# partial_lockdown - EXPANDED. Bounded requests with no emergency framing.
# Each seed is a DIFFERENT situation, not a rephrasing - the model scored
# 0.000 on this class because 6 seeds became 81 near-identical messages.
# ---------------------------------------------------------------------------
add("i used the library computer yesterday, can you sign me out of instagram there", "partial_lockdown", "owner", "calm", "only", ["instagram"])
add("logged into telegram on my old laptop which i sold, please kill that session", "partial_lockdown", "owner", "worried", "only", ["telegram"])
add("my ex might still have access to my instagram, log out everything", "partial_lockdown", "owner", "worried", "only", ["instagram"])
add("routine security check, rotate my whatsapp password please", "partial_lockdown", "owner", "calm", "only", ["whatsapp"])
add("i shared my netflix password with someone and reused it on instagram, change it", "partial_lockdown", "owner", "worried", "only", ["instagram"])
add("sign me out of gmail on all devices, i want a clean slate", "partial_lockdown", "owner", "calm", "only", ["gmail"])
add("can you kill my bank session, i forgot to log out at the cyber cafe", "partial_lockdown", "owner", "worried", "only", ["demobank"])
add("please refresh my telegram password, it is quite old now", "partial_lockdown", "owner", "calm", "only", ["telegram"])
add("just do instagram and whatsapp, log out everywhere", "partial_lockdown", "owner", "calm", "only", ["instagram", "whatsapp"])
add("i think my roommate knows my gmail password, rotate it", "partial_lockdown", "owner", "worried", "only", ["gmail"])
add("Kindly sign out all active sessions on my banking profile.", "partial_lockdown", "owner", "calm", "only", ["demobank"])
add("change my whatsapp and telegram passwords, nothing else needed", "partial_lockdown", "owner", "calm", "only", ["whatsapp", "telegram"])
add("bank ka password change kar do please, purana ho gaya hai", "partial_lockdown", "owner", "calm", "only", ["demobank"], lang="hi-en")
add("gmail se sab devices logout kar do, koi emergency nahi hai bas safety", "partial_lockdown", "owner", "calm", "only", ["gmail"], lang="hi-en")
add("no emergency, just log me out of instagram please", "partial_lockdown", "owner", "calm", "only", ["instagram"])
add("i want to remove all old devices from my whatsapp account", "partial_lockdown", "owner", "calm", "only", ["whatsapp"])
add("someone borrowed my laptop last week, sign me out of telegram to be safe", "partial_lockdown", "owner", "worried", "only", ["telegram"])
add("Please deactivate all sessions on my email account as a precaution.", "partial_lockdown", "owner", "calm", "only", ["gmail"])
add("clean up my bank sessions, i have logged in from too many places", "partial_lockdown", "owner", "calm", "only", ["demobank"])

# ---------------------------------------------------------------------------
# status_query - EXPANDED. Recall was 0.190 on 6 seeds.
# ---------------------------------------------------------------------------
add("has anything happened yet? i sent a mail 5 minutes ago", "status_query", "owner", "worried")
add("which of my accounts have you locked so far", "status_query", "owner", "worried")
add("is the bank freeze active or still pending", "status_query", "owner", "worried")
add("i never got a confirmation, did it work", "status_query", "owner", "worried")
add("Please provide a summary of the actions taken on my account.", "status_query", "owner", "calm")
add("checking in - what is the current state of my accounts", "status_query", "owner", "calm")
add("was instagram included in the lockdown or not", "status_query", "owner", "worried")
add("did you get my earlier message about the phone", "status_query", "owner", "worried")
add("STATUS?? did everything go through??", "status_query", "owner", "panic")
add("can you tell me if my email is still locked", "status_query", "owner", "calm")
add("mera bank freeze hua ya nahi, please batao", "status_query", "owner", "worried", lang="hi-en")
add("kitne accounts lock ho gaye ab tak", "status_query", "owner", "calm", lang="hi-en")
add("just want to confirm the lockdown finished", "status_query", "owner", "calm")
add("what is the incident number for my request", "status_query", "owner", "calm")

# ---------------------------------------------------------------------------
# verification_response - EXPANDED. Answers to challenge questions, with the
# hedging and partial recall a stressed person actually produces.
# ---------------------------------------------------------------------------
add("bruno", "verification_response", "owner", "calm")
add("her dog, bruno", "verification_response", "owner", "calm")
add("BRUNO the dog", "verification_response", "owner", "panic")
add("um bruno i think, the brown one", "verification_response", "owner", "worried")
add("my grandmother had a dog named bruno", "verification_response", "owner", "calm")
add("nani ka kutta bruno tha", "verification_response", "owner", "calm", lang="hi-en")
add("i opened that account in ghaziabad", "verification_response", "owner", "calm")
add("ghaziabad. definitely ghaziabad.", "verification_response", "owner", "worried")
add("it was in ghaziabad, near the old market branch", "verification_response", "owner", "calm")
add("first school was st marys convent", "verification_response", "owner", "calm")
add("st. mary's", "verification_response", "owner", "calm")
add("i went to st marys convent school as a kid", "verification_response", "owner", "calm")
add("sorry my mind is blank, is it bruno?", "verification_response", "owner", "panic")
add("the answer is bruno", "verification_response", "owner", "calm")

# ---------------------------------------------------------------------------
# HARD NEGATIVES that look like lost_uncertain. This is the 38-instance
# confusion from the M1 eval: out_of_scope being read as a real emergency.
# Losing a non-phone object, or someone else losing theirs, must never act.
# ---------------------------------------------------------------------------
add("i lost my keys somewhere in the house again", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("cant find my earphones anywhere, so annoying", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("lost my umbrella in the metro yesterday", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("my sister lost her phone at college today", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("i misplaced my student id card, need to get a new one", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("lost my water bottle at the gym", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("my mom keeps losing her reading glasses", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("cant find the charger, did you take it", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("i lost my train ticket, have to buy another one", "out_of_scope", "mere_mention", "worried", hard_negative=True)
add("my friend cannot find her phone but she thinks its at home", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("lost my notebook with all my notes in it, disaster", "out_of_scope", "mere_mention", "worried", hard_negative=True)
add("chabi kho gayi hai, dhundh raha hoon", "out_of_scope", "mere_mention", "calm", hard_negative=True, lang="hi-en")
add("he lost his laptop bag on the bus last month", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("i lost track of time and missed the meeting", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("losing my patience with this software honestly", "out_of_scope", "mere_mention", "worried", hard_negative=True)
add("my phone is at home, i left it charging, using laptop", "out_of_scope", "owner", "calm", hard_negative=True)
add("i cant find my phone case, the phone itself is fine", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("lost connection to wifi again", "out_of_scope", "mere_mention", "calm", hard_negative=True)

# ---------------------------------------------------------------------------
# proxy - topping up toward the 12% target
# ---------------------------------------------------------------------------
add("her phone was taken at the bus stop, she is with me and asked me to write", "stolen_confirmed", "proxy", "worried")
add("this is her mother. someone stole her phone. please secure her accounts.", "stolen_confirmed", "proxy", "worried")
add("writing for my flatmate, phone snatched outside our building 10 mins ago", "stolen_confirmed", "proxy", "panic")
add("she is crying, her phone got robbed, do whatever needs doing", "stolen_confirmed", "proxy", "panic")
add("rebecca cannot email you herself, her phone is gone. she asked me.", "stolen_confirmed", "proxy", "worried")
add("her bag with the phone was stolen from the cafe, im her colleague", "stolen_confirmed", "proxy", "worried")
add("uska phone chori ho gaya, usne mujhe aapko likhne ko bola", "stolen_confirmed", "proxy", "worried", lang="hi-en")
add("This is her father writing. Device stolen. Please act.", "stolen_confirmed", "proxy", "calm")
add("my friend thinks she left her phone in the auto, asked me to mail you", "lost_uncertain", "proxy", "calm")
add("her phone is missing since this morning, she wants sessions cleared", "lost_uncertain", "proxy", "worried")

# ---------------------------------------------------------------------------
# code-mixed - topping up toward the 15% target
# ---------------------------------------------------------------------------
add("yaar mera phone gaya, sab band karo abhi", "stolen_confirmed", "owner", "panic", lang="hi-en")
add("metro station pe phone snatch kar liya kisi ne, help karo", "stolen_confirmed", "owner", "panic", lang="hi-en")
add("phone chori ho gaya par email mat lock karna abhi", "stolen_confirmed", "owner", "worried", "except", ["gmail"], lang="hi-en")
add("sirf bank account lock karo, baaki kuch nahi", "partial_lockdown", "owner", "calm", "only", ["demobank"], lang="hi-en")
add("mera phone nahi mil raha, ghar pe hi hoga", "lost_uncertain", "owner", "calm", lang="hi-en")
add("ruko ruko phone mil gaya, kuch mat karo", "cancel_false_alarm", "owner", "worried", lang="hi-en")
add("galti se mail kiya tha, cancel karo sab", "cancel_false_alarm", "owner", "calm", lang="hi-en")
add("instagram aur whatsapp dono lock kar do, phone chori hua hai", "stolen_confirmed", "owner", "worried", "only", ["instagram", "whatsapp"], lang="hi-en")
add("uska phone kho gaya tha pichle hafte, ab mil gaya", "out_of_scope", "mere_mention", "calm", hard_negative=True, lang="hi-en")
add("news me dekha phone chori bahut badh gayi hai", "out_of_scope", "mere_mention", "calm", hard_negative=True, lang="hi-en")

# ---------------------------------------------------------------------------
# ROUND 3 SEEDS - lifting every class above 5 test seeds.
# Target ~34 seeds per intent so a 15% split leaves 5+ situations in test.
# Each entry is a DIFFERENT situation. Hinglish is spread across all classes
# rather than clustered, because a code-mixed status_query was an empty cell.
# ---------------------------------------------------------------------------

# --- lost_uncertain: 18 -> 34 ---
add("i think my phone slipped out of my pocket in the auto", "lost_uncertain", "owner", "worried")
add("phone not in my bag, i had it at the restaurant an hour ago", "lost_uncertain", "owner", "worried")
add("cant locate my phone since the wedding last night", "lost_uncertain", "owner", "calm")
add("My phone appears to be missing. I would like sessions cleared as a precaution.", "lost_uncertain", "owner", "calm")
add("left my phone on the train i think, going to lost and found now", "lost_uncertain", "owner", "worried")
add("i have looked everywhere in the flat and no phone", "lost_uncertain", "owner", "worried")
add("phone is gone but i doubt anyone took it, probably dropped it", "lost_uncertain", "owner", "calm")
add("missing phone since the cricket match, huge crowd there", "lost_uncertain", "owner", "worried")
add("i cant find my phone and its not ringing when i call it", "lost_uncertain", "owner", "worried")
add("phone disappeared somewhere between office and home", "lost_uncertain", "owner", "worried")
add("lost the phone at the airport, filing a report but sign me out first", "lost_uncertain", "owner", "worried")
add("mera phone kahin gir gaya hai, mil nahi raha", "lost_uncertain", "owner", "worried", lang="hi-en")
add("phone nahi mil raha subah se, sessions clear kar do", "lost_uncertain", "owner", "worried", lang="hi-en")
add("auto me phone chhoot gaya lagta hai", "lost_uncertain", "owner", "calm", lang="hi-en")
add("i probably left it at my friends place but log me out anyway", "lost_uncertain", "owner", "calm")
add("phone missing, no idea if dropped or taken, being careful", "lost_uncertain", "owner", "worried")

# --- cancel_false_alarm: 15 -> 34 ---
add("ignore my last mail, the phone was under the pillow", "cancel_false_alarm", "owner", "calm")
add("STOP everything, i found the phone", "cancel_false_alarm", "owner", "panic")
add("sorry sorry my mistake, no lockdown needed", "cancel_false_alarm", "owner", "worried")
add("the phone was with my sister all along, cancel please", "cancel_false_alarm", "owner", "calm")
add("recovered the phone from the lost and found, reverse everything", "cancel_false_alarm", "owner", "calm")
add("I wish to withdraw my earlier request. The device has been located.", "cancel_false_alarm", "owner", "calm")
add("hold on, dont do anything, i think i overreacted", "cancel_false_alarm", "owner", "worried")
add("it was in the car the whole time, please undo", "cancel_false_alarm", "owner", "calm")
add("someone returned my phone to the security desk, cancel the lockdown", "cancel_false_alarm", "owner", "calm")
add("my mistake, i sent that mail by accident", "cancel_false_alarm", "owner", "calm")
add("abort abort, phone is here", "cancel_false_alarm", "owner", "panic")
add("please roll back whatever you did, everything is fine now", "cancel_false_alarm", "owner", "calm")
add("phone wapas mil gaya, sab undo kar do please", "cancel_false_alarm", "owner", "calm", lang="hi-en")
add("galat alarm tha, kuch mat karo", "cancel_false_alarm", "owner", "worried", lang="hi-en")
add("cancel karo, mere bhai ne liya tha phone", "cancel_false_alarm", "owner", "calm", lang="hi-en")
add("do not proceed with the lockdown, situation resolved", "cancel_false_alarm", "owner", "calm")
add("i got it back from the guy, he was returning it", "cancel_false_alarm", "owner", "calm")
add("scratch that last message please", "cancel_false_alarm", "owner", "calm")
add("no longer needed, found the phone in my jacket", "cancel_false_alarm", "owner", "calm")

# --- verification_response: 21 -> 34 ---
add("it was bruno, i am certain", "verification_response", "owner", "calm")
add("bruno. brown labrador.", "verification_response", "owner", "calm")
add("the dog? bruno. next question.", "verification_response", "owner", "worried")
add("i already told you, bruno", "verification_response", "owner", "worried")
add("BRUNO", "verification_response", "owner", "panic")
add("bruno bruno bruno please hurry", "verification_response", "owner", "panic")
add("opened it at the ghaziabad branch", "verification_response", "owner", "calm")
add("ghaziabad, uttar pradesh", "verification_response", "owner", "calm")
add("that would be ghaziabad", "verification_response", "owner", "calm")
add("school was st marys, the convent one", "verification_response", "owner", "calm")
add("saint marys convent school", "verification_response", "owner", "calm")
add("bruno tha uska naam", "verification_response", "owner", "calm", lang="hi-en")
add("ghaziabad me account khola tha", "verification_response", "owner", "calm", lang="hi-en")

# --- status_query: 20 -> 34 ---
add("any update on my request from earlier", "status_query", "owner", "worried")
add("i want to know exactly what was locked and what was not", "status_query", "owner", "calm")
add("has the email been secured yet or not", "status_query", "owner", "worried")
add("is the process still running or has it finished", "status_query", "owner", "worried")
add("Could you confirm receipt and the current progress?", "status_query", "owner", "calm")
add("nothing has come back to me yet, whats going on", "status_query", "owner", "worried")
add("tell me what state my accounts are in right now", "status_query", "owner", "worried")
add("did the second stage complete", "status_query", "owner", "calm")
add("i just want confirmation before i go to the police", "status_query", "owner", "worried")
add("update kya hai, kuch pata chala", "status_query", "owner", "worried", lang="hi-en")
add("email lock hua ki nahi, confirm karo", "status_query", "owner", "worried", lang="hi-en")
add("process complete ho gaya kya", "status_query", "owner", "calm", lang="hi-en")
add("sab theek hai na, sab lock ho gaya", "status_query", "owner", "worried", lang="hi-en")
add("was my earlier email even received", "status_query", "owner", "worried")

# --- partial_lockdown: 26 -> 34 ---
add("please end my instagram session on the office desktop", "partial_lockdown", "owner", "calm", "only", ["instagram"])
add("rotate the bank password, i want a stronger one", "partial_lockdown", "owner", "calm", "only", ["demobank"])
add("kick out all telegram sessions except this device", "partial_lockdown", "owner", "calm", "only", ["telegram"])
add("i gave my old phone to my cousin, remove whatsapp from it", "partial_lockdown", "owner", "calm", "only", ["whatsapp"])
add("gmail password change kar do, koi urgency nahi", "partial_lockdown", "owner", "calm", "only", ["gmail"], lang="hi-en")
add("telegram ke saare sessions band kar do", "partial_lockdown", "owner", "calm", "only", ["telegram"], lang="hi-en")
add("just refresh my instagram credentials please", "partial_lockdown", "owner", "calm", "only", ["instagram"])
add("sign out of the bank everywhere, doing a security cleanup today", "partial_lockdown", "owner", "calm", "only", ["demobank"])

# --- more stolen_confirmed / out_of_scope so the big classes keep pace ---
add("two guys on a scooter took my phone right out of my hand", "stolen_confirmed", "owner", "panic")
add("phone stolen from my locker at the gym, lock everything", "stolen_confirmed", "owner", "worried")
add("someone broke into my car and took the phone off the seat", "stolen_confirmed", "owner", "worried")
add("my phone was taken during the concert, it was unlocked", "stolen_confirmed", "owner", "panic")
add("bag snatched at the traffic signal with my phone inside", "stolen_confirmed", "owner", "panic")
add("i watched someone walk off with my phone and i could not stop them", "stolen_confirmed", "owner", "panic")
add("bike wale ne phone cheen liya, sab lock karo", "stolen_confirmed", "owner", "panic", lang="hi-en")
add("gym locker se phone chori ho gaya", "stolen_confirmed", "owner", "worried", lang="hi-en")
add("my subscription renewal failed, please update the card", "out_of_scope", "owner", "calm", hard_negative=True)
add("can we reschedule tomorrows call to friday", "out_of_scope", "owner", "calm", hard_negative=True)
add("the wifi password needs changing, too many people know it", "out_of_scope", "owner", "calm", hard_negative=True)
add("i am locked out of my own house, forgot the keys inside", "out_of_scope", "mere_mention", "worried", hard_negative=True)
add("please freeze my gym membership for two months", "out_of_scope", "owner", "calm", hard_negative=True)
add("account statement galat aaya hai, check karo", "out_of_scope", "owner", "calm", hard_negative=True, lang="hi-en")

# ---------------------------------------------------------------------------
# ROUND 4 - HARD NEGATIVES, targeted at the specific confusions in the M1 eval.
#
# FTR was 0.372 while macro-F1 was 0.798: the model learned to say "emergency"
# readily, which fixed recall on the emergency classes and cost precision on
# out_of_scope. These seeds exist purely to teach it when NOT to act.
#
# Confusion counts driving the weighting:
#   out_of_scope -> lost_uncertain     x46
#   out_of_scope -> status_query       x29
#   out_of_scope -> partial_lockdown   x17
# ---------------------------------------------------------------------------

# --- looks like lost_uncertain, must do nothing (x46 confusion) ---
add("i lost my train of thought halfway through the meeting", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("lost my voice after shouting at the match yesterday", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("we lost the game 3-1, terrible defending", "out_of_scope", "mere_mention", "worried", hard_negative=True)
add("i think i lost a follower on instagram lol", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("lost my appetite completely after that news", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("cant find the file i saved yesterday on my laptop", "out_of_scope", "mere_mention", "worried", hard_negative=True)
add("misplaced the charger cable somewhere in the office", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("i lost my place in the book, forgot to bookmark", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("my brother lost his phone but he has already sorted it out", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("she misplaced her wallet at the mall last weekend", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("lost my sunglasses again, that is the fourth pair", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("i cant find the remote, check under the sofa", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("the courier lost my package, filing a complaint", "out_of_scope", "mere_mention", "worried", hard_negative=True)
add("i lost my earring somewhere between here and the parking lot", "out_of_scope", "mere_mention", "worried", hard_negative=True)
add("phone battery died, not lost, just dead", "out_of_scope", "owner", "calm", hard_negative=True)
add("my phone is at the repair shop for two days", "out_of_scope", "owner", "calm", hard_negative=True)
add("left my phone at home today, using the office landline", "out_of_scope", "owner", "calm", hard_negative=True)
add("chabi kho gayi thi par mil gayi", "out_of_scope", "mere_mention", "calm", hard_negative=True, lang="hi-en")
add("mera wallet kho gaya, phone theek hai", "out_of_scope", "mere_mention", "worried", hard_negative=True, lang="hi-en")
add("uska phone kho gaya tha college me", "out_of_scope", "mere_mention", "calm", hard_negative=True, lang="hi-en")
add("i lost interest in that series after season two", "out_of_scope", "mere_mention", "calm", hard_negative=True)
add("we lost power for three hours last night", "out_of_scope", "mere_mention", "calm", hard_negative=True)

# --- looks like status_query, must do nothing (x29 confusion) ---
add("any update on the delivery i ordered last week", "out_of_scope", "owner", "calm", hard_negative=True)
add("did you get a chance to look at the document i sent", "out_of_scope", "owner", "calm", hard_negative=True)
add("whats the status of my leave application", "out_of_scope", "owner", "calm", hard_negative=True)
add("has the refund been processed yet", "out_of_scope", "owner", "worried", hard_negative=True)
add("is the server back up or still down", "out_of_scope", "owner", "worried", hard_negative=True)
add("did my payment go through for the electricity bill", "out_of_scope", "owner", "worried", hard_negative=True)
add("what happened with the ticket booking, did it confirm", "out_of_scope", "owner", "worried", hard_negative=True)
add("can you confirm the meeting time for tomorrow", "out_of_scope", "owner", "calm", hard_negative=True)
add("is the report ready or should i wait", "out_of_scope", "owner", "calm", hard_negative=True)
add("order ka status kya hai, aaya nahi abhi tak", "out_of_scope", "owner", "worried", hard_negative=True, lang="hi-en")
add("refund process hua ki nahi", "out_of_scope", "owner", "worried", hard_negative=True, lang="hi-en")
add("did anyone check whether the printer is working", "out_of_scope", "owner", "calm", hard_negative=True)
add("update me on the project deadline please", "out_of_scope", "owner", "calm", hard_negative=True)

# --- looks like partial_lockdown, must do nothing (x17 confusion) ---
add("log out of netflix on the living room tv please", "out_of_scope", "owner", "calm", hard_negative=True)
add("i need to change my wifi password, too many devices", "out_of_scope", "owner", "calm", hard_negative=True)
add("please freeze my gym membership for the summer", "out_of_scope", "owner", "calm", hard_negative=True)
add("can you lock the meeting room for 3pm", "out_of_scope", "owner", "calm", hard_negative=True)
add("block that spam number on my behalf", "out_of_scope", "owner", "calm", hard_negative=True)
add("suspend my newspaper subscription while i travel", "out_of_scope", "owner", "calm", hard_negative=True)
add("remove my old address from the delivery app", "out_of_scope", "owner", "calm", hard_negative=True)
add("i want to deactivate my twitter, not the others", "out_of_scope", "owner", "calm", hard_negative=True)
add("please reset the printer password in the office", "out_of_scope", "owner", "calm", hard_negative=True)
add("freeze the hiring for this quarter as discussed", "out_of_scope", "owner", "calm", hard_negative=True)
add("netflix se logout kar do tv pe", "out_of_scope", "owner", "calm", hard_negative=True, lang="hi-en")
add("wifi ka password change karna hai", "out_of_scope", "owner", "calm", hard_negative=True, lang="hi-en")

# --- phishing and security spam: mention accounts and urgency, must do nothing ---
add("URGENT: your account will be suspended unless you verify now", "out_of_scope", "owner", "panic", hard_negative=True)
add("We detected a login from a new device. Was this you?", "out_of_scope", "owner", "worried", hard_negative=True)
add("Your password expires in 3 days. Update it to avoid lockout.", "out_of_scope", "owner", "calm", hard_negative=True)
add("Security alert: unusual activity on your banking profile. Click to review.", "out_of_scope", "owner", "worried", hard_negative=True)
add("Final notice: verify your identity or your account will be frozen", "out_of_scope", "owner", "panic", hard_negative=True)
add("Monthly security digest: 3 tips to keep your phone safe", "out_of_scope", "owner", "calm", hard_negative=True)
add("Someone tried to reset your password. If this was not you, ignore this email.", "out_of_scope", "owner", "worried", hard_negative=True)
add("Your two factor authentication code is 449182. Do not share it.", "out_of_scope", "owner", "calm", hard_negative=True)

# --- proxy top-up: fell to 7.9% when the corpus grew ---
add("her phone was stolen at the market, im her neighbour writing for her", "stolen_confirmed", "proxy", "worried")
add("this is her cousin, someone grabbed her phone near the station", "stolen_confirmed", "proxy", "panic")
add("writing for rebecca, phone taken from her hand at the signal", "stolen_confirmed", "proxy", "panic")
add("she is at the police station, her phone was robbed, please lock things", "stolen_confirmed", "proxy", "worried")
add("On her behalf: device stolen this evening, requesting full lockdown.", "stolen_confirmed", "proxy", "calm")
add("her phone got snatched, she cannot mail you herself obviously", "stolen_confirmed", "proxy", "worried")
add("bhabhi ka phone chori ho gaya, unhone kaha mail kar dun", "stolen_confirmed", "proxy", "worried", lang="hi-en")
add("uska phone cheen liya kisi ne, please help karo", "stolen_confirmed", "proxy", "panic", lang="hi-en")
add("my friend cannot find her phone, she asked me to get her signed out", "lost_uncertain", "proxy", "calm")
add("her phone is missing, writing on her request", "lost_uncertain", "proxy", "calm")

# ---------------------------------------------------------------------------
# ROUND 5 - closing the two composition gaps flagged by build_dataset.py.
#
#   proxy role   9.2% vs 12% target, and misread as owner 27.5% of the time -
#                a security gap, since proxy messages are meant to take the
#                strictest verification path and cap at Tier 1.
#   scope=except 7 seeds total, ONE of them in the test split. The best demo
#                case in the project is currently measured on one situation.
# ---------------------------------------------------------------------------

# --- scope=except: 7 -> 30 seeds. The inversion case. ---
add("phone stolen, lock it all except whatsapp, my mother needs to reach me", "stolen_confirmed", "owner", "worried", "except", ["whatsapp"])
add("someone took my phone. everything except the bank, i have a payment clearing", "stolen_confirmed", "owner", "worried", "except", ["demobank"])
add("lock everything other than instagram, i need it for work today", "stolen_confirmed", "owner", "calm", "except", ["instagram"])
add("stolen! all accounts but not telegram please", "stolen_confirmed", "owner", "panic", "except", ["telegram"])
add("my phone is gone. lock everything, leave out my email for now", "stolen_confirmed", "owner", "worried", "except", ["gmail"])
add("do the full lockdown apart from whatsapp and instagram", "stolen_confirmed", "owner", "worried", "except", ["whatsapp", "instagram"])
add("phone snatched, everything except gmail and the bank", "stolen_confirmed", "owner", "panic", "except", ["gmail", "demobank"])
add("Please secure all accounts with the exception of my email.", "stolen_confirmed", "owner", "calm", "except", ["gmail"])
add("lock them all, skip telegram, i am mid conversation with the police", "stolen_confirmed", "owner", "panic", "except", ["telegram"])
add("everything but the bank account, i will call them myself", "stolen_confirmed", "owner", "worried", "except", ["demobank"])
add("phone stolen. all except instagram.", "stolen_confirmed", "owner", "calm", "except", ["instagram"])
add("i lost my phone, lock everything other than whatsapp", "lost_uncertain", "owner", "worried", "except", ["whatsapp"])
add("sab lock karo, email chhod do abhi", "stolen_confirmed", "owner", "worried", "except", ["gmail"], lang="hi-en")
add("phone chori ho gaya, whatsapp ke alawa sab band karo", "stolen_confirmed", "owner", "panic", "except", ["whatsapp"], lang="hi-en")
add("bank chhod ke baaki sab lock kar do", "stolen_confirmed", "owner", "worried", "except", ["demobank"], lang="hi-en")
add("instagram ko chhod do, baaki sab lock", "stolen_confirmed", "owner", "calm", "except", ["instagram"], lang="hi-en")
add("her phone was taken - lock everything except her email, she needs it", "stolen_confirmed", "proxy", "worried", "except", ["gmail"])
add("she says lock it all apart from whatsapp", "stolen_confirmed", "proxy", "worried", "except", ["whatsapp"])
add("full lockdown minus the bank please", "stolen_confirmed", "owner", "worried", "except", ["demobank"])
add("everything except telegram and whatsapp, phone was robbed", "stolen_confirmed", "owner", "panic", "except", ["telegram", "whatsapp"])
add("stolen phone. secure all accounts, excluding my email.", "stolen_confirmed", "owner", "calm", "except", ["gmail"])
add("lock the lot, just not instagram", "stolen_confirmed", "owner", "worried", "except", ["instagram"])
add("do everything besides the bank account", "stolen_confirmed", "owner", "worried", "except", ["demobank"])

# --- the ESPECIALLY counterpart. These share almost all vocabulary with the
#     block above and differ by one token, inverting the action set. Both must
#     be present in quantity or the model learns the target name, not the
#     operator.
add("phone stolen! lock everything and especially whatsapp", "stolen_confirmed", "owner", "panic", "all", ["whatsapp"])
add("someone took my phone, lock it all, above all the bank", "stolen_confirmed", "owner", "panic", "all", ["demobank"])
add("lock everything, particularly my instagram", "stolen_confirmed", "owner", "worried", "all", ["instagram"])
add("stolen! all accounts and definitely telegram", "stolen_confirmed", "owner", "panic", "all", ["telegram"])
add("my phone is gone. lock everything, most importantly my email", "stolen_confirmed", "owner", "panic", "all", ["gmail"])
add("full lockdown, make sure whatsapp and instagram are included", "stolen_confirmed", "owner", "worried", "all", ["whatsapp", "instagram"])
add("Please secure all accounts, my email in particular.", "stolen_confirmed", "owner", "calm", "all", ["gmail"])
add("sab lock karo, khaas kar ke email", "stolen_confirmed", "owner", "panic", "all", ["gmail"], lang="hi-en")
add("bank samet sab kuch band karo", "stolen_confirmed", "owner", "worried", "all", ["demobank"], lang="hi-en")

# --- proxy: 33 -> 60 seeds ---
add("i am her manager, her phone was stolen during the site visit", "stolen_confirmed", "proxy", "worried")
add("this is the hostel warden, a student's phone was snatched outside", "stolen_confirmed", "proxy", "worried")
add("her husband here. phone taken at the market. she wants everything locked.", "stolen_confirmed", "proxy", "worried")
add("i work with rebecca, someone grabbed her phone in the lobby just now", "stolen_confirmed", "proxy", "panic")
add("she handed me this address before going to the police, phone was robbed", "stolen_confirmed", "proxy", "worried")
add("writing because she cannot - her phone is with the thief", "stolen_confirmed", "proxy", "worried")
add("Her device was stolen this afternoon. I am contacting you at her request.", "stolen_confirmed", "proxy", "calm")
add("my daughter's phone got snatched near the college gate", "stolen_confirmed", "proxy", "panic")
add("this is her tuition teacher, her phone was taken from the classroom", "stolen_confirmed", "proxy", "worried")
add("she is shaken, phone stolen at the station, please act on her behalf", "stolen_confirmed", "proxy", "panic")
add("her phone got taken and she asked me to write from my account", "stolen_confirmed", "proxy", "worried")
add("i am a bystander, she asked me to email you, her phone was snatched", "stolen_confirmed", "proxy", "panic")
add("bhai uska phone chori ho gaya, usne mujhse mail karne ko bola", "stolen_confirmed", "proxy", "worried", lang="hi-en")
add("meri behen ka phone cheen liya, please help karo", "stolen_confirmed", "proxy", "panic", lang="hi-en")
add("uski taraf se likh raha hoon, phone gaya hai", "stolen_confirmed", "proxy", "worried", lang="hi-en")
add("dost ka phone kho gaya, usne bola aapko batau", "lost_uncertain", "proxy", "calm", lang="hi-en")
add("her phone is missing since the morning, she asked me to get her signed out", "lost_uncertain", "proxy", "calm")
add("my colleague cannot find her phone, writing on her behalf", "lost_uncertain", "proxy", "calm")
add("she thinks she left it in the cab, wants sessions cleared just in case", "lost_uncertain", "proxy", "worried")
add("this is her sister - false alarm, she found the phone", "cancel_false_alarm", "proxy", "calm")
add("she got her phone back, please cancel the request i sent", "cancel_false_alarm", "proxy", "calm")
add("ignore my earlier mail, her phone turned up", "cancel_false_alarm", "proxy", "calm")
add("she is asking what happened with her accounts", "status_query", "proxy", "worried")
add("can you tell me if her lockdown went through, she wants to know", "status_query", "proxy", "worried")
add("On her behalf - could you confirm which accounts were secured?", "status_query", "proxy", "calm")
add("she asked me to check the status for her", "status_query", "proxy", "calm")
add("uska status pata karna hai, usne pucha", "status_query", "proxy", "worried", lang="hi-en")

# --- minimal-phrasing lost_uncertain. Fixes the xfail regression: bare
#     "I lost my phone" with no context is currently read as out_of_scope,
#     because round 4 taught the model that "lost X" usually means nothing.
add("I lost my phone", "lost_uncertain", "owner", "calm")
add("lost my phone", "lost_uncertain", "owner", "calm")
add("my phone is lost", "lost_uncertain", "owner", "calm")
add("i lost my phone.", "lost_uncertain", "owner", "calm")
add("phone lost", "lost_uncertain", "owner", "calm")
add("I have lost my phone", "lost_uncertain", "owner", "calm")
add("lost the phone", "lost_uncertain", "owner", "calm")
add("my phone got lost", "lost_uncertain", "owner", "calm")
add("phone kho gaya", "lost_uncertain", "owner", "calm", lang="hi-en")
add("mera phone kho gaya hai", "lost_uncertain", "owner", "calm", lang="hi-en")