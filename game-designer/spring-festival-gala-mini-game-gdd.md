# Game Design Document: "Wan Jia Deng Huo" (Ten Thousand Homes Ablaze)
# 万家灯火 -- Spring Festival Gala Mini-Game

> **Agent ID**: GD-001
> **Version**: 1.0
> **Date**: 2026-02-16
> **Task**: WP-4.1 Designer Slot -- Spring Festival Gala Interactive Mini-Game
> **Status**: Complete

---

## 1. Executive Summary

**Game Title**: Wan Jia Deng Huo (万家灯火 / Ten Thousand Homes Ablaze)

**One-Line Pitch**: Families light lanterns together across a shared virtual village, with each generation contributing unique actions, racing to illuminate all of China before the midnight countdown.

**Genre**: Cooperative casual / party game (family co-op with competitive server-wide race)

**Platform**: WeChat Mini Program (primary), mobile web (fallback), TV spectator mode (passive)

**Target Audience**: Multi-generational Chinese families watching the Spring Festival Gala (ages 6-80+, 800M+ potential viewers)

**Session Length**: 3-5 minutes per round; game spans the full Chunwan broadcast (~4.5 hours) with synchronized moments

**Player Count**: 2-8 per family team; millions of families competing server-wide

**Unique Selling Proposition**: The first Chunwan interactive game designed for **cooperative multi-generational play** -- where grandma's simple tap and grandchild's quick reflexes both matter equally, and the whole family contributes to a shared spectacle visible on the TV screen.

---

## 2. Game Concept

### Core Fantasy

You and your family are lighting lanterns to bring warmth and light to your virtual village as the New Year arrives. Each family member has a role suited to their ability. Grandpa shakes his phone to "strike the flint." Mom taps to "hang the lantern." The kid plays a quick reflex game to "chase away the Nian beast" and protect the lanterns. Together, you illuminate your family's home -- and your light joins millions of others across a virtual map of China, creating a collective fireworks-and-lanterns spectacle at midnight.

The emotional arc: **warmth** (lighting your home together) -> **tension** (will we finish before midnight?) -> **shared pride** (our family's light is part of the national display) -> **celebration** (the midnight fireworks, powered by everyone's lanterns).

### Unique Selling Proposition: Why THIS Game for Chunwan

1. **No Chunwan game has ever been truly cooperative across generations.** Alipay Fu collection is solo. WeChat shake was individual. This game requires the family to work together, which directly embodies the core Chunwan emotion: tuanyuan (reunion). [Research Report, Recommendation 1]

2. **The Horse year theme is mechanically integrated, not just decorative.** The Lucky Horse (Jixiang Ma) gallops across the village carrying special golden lanterns. Players must time their taps to catch the galloping horse -- a direct reference to the 2026 Matafeiyan (Galloping Horse Treading on a Swallow) mascot. [Research Report, Section 4]

3. **Cooperative + competitive dual structure.** Each family cooperates internally, but ALL families compete on a national map to see which province lights up first. This creates community pride without pitting family members against each other. [Precedent: Fall Guys team rounds; Jackbox Games cooperative scoring]

4. **TV spectator mode.** Non-participating family members watching the Chunwan broadcast see a live overlay (or companion web page on the smart TV) showing the national lantern map lighting up in real-time. The game is entertaining to WATCH even without playing. [Research Report, Anti-Pattern 8.4]

### Spring Festival Cultural Hooks

| Cultural Element | Mechanical Integration | Emotional Function |
|-----------------|----------------------|-------------------|
| Lantern lighting (deng) | Core mechanic: each interaction lights a lantern in the village | Warmth, home, prosperity |
| Nian beast (nian shou) | Reflex mini-game: tap to scare away the beast before it extinguishes lanterns | Tension, protection, courage |
| Red envelopes (hongbao) | Reward mechanic: completing family tasks earns instant mini-hongbao + cumulative horse collectibles | Generosity, luck, surprise |
| Horse year (Jixiang Ma) | Timing mechanic: catch the galloping horse for bonus golden lanterns | Speed, aspiration, cultural pride |
| Family reunion (tuanyuan) | Team structure: family members must cooperate; more family = faster lighting | Togetherness, belonging |
| Spring couplets (chunlian) | AI personalization: family earns a custom AI-generated couplet based on their play style at game end | Cultural knowledge, shareability |
| Fireworks (yanhua) | Climax event: all families' lanterns trigger a collective virtual fireworks display at midnight | Celebration, community |

### Three Designed "Fun Moments"

1. **"We did it together!" moment**: The instant your family's village is fully lit. The screen erupts with warm golden light, a congratulations banner unfurls, and you see your family members' avatars standing together in the glowing village. Grandma's phone vibrates with a gentle "ding" even if she is not looking at the screen. This moment works because each person contributed -- grandma shook, dad tapped, the kid defended. No single person could have done it alone.

2. **"The horse is coming!" moment**: During synchronized broadcast moments (see Section 5), the Lucky Horse gallops across everyone's screen simultaneously. The entire family shouts "kuai kuai kuai!" (quick quick quick!) as they tap to catch it. The horse appears for only 5 seconds. If ANY family member catches it, the whole family gets the golden lantern. This creates shared excitement and lets the fastest family member be the hero.

3. **"Look, that's our light!" moment**: At midnight, the national map shows every family's lantern contribution. You can zoom into your province and see your family's village glowing among thousands of others. The collective display -- millions of tiny lights forming the shape of China -- is visible on the TV broadcast companion page. The feeling: "We were part of this. Our little family's light is up there with everyone else's."

---

## 3. Core Mechanics

### Core Loop Diagram

```
                    +-----------+
                    |  START    |
                    | (Join as  |
                    |  Family)  |
                    +-----+-----+
                          |
                          v
               +----------+----------+
               |  FAMILY HUB         |
               |  See your dark      |
               |  village, assign    |
               |  roles              |
               +----------+----------+
                          |
              +-----------+-----------+
              |           |           |
              v           v           v
        +-----+---+ +----+----+ +----+----+
        | SHAKE   | | TAP     | | DEFEND  |
        | (Elder) | | (Adult) | | (Youth) |
        | Strike  | | Hang    | | Chase   |
        | flint   | | lantern | | Nian    |
        +---------+ +---------+ +---------+
              |           |           |
              +-----------+-----------+
                          |
                          v
                 +--------+--------+
                 | LANTERN LIT!    |
                 | +1 to village   |
                 | Mini-hongbao    |
                 +--------+--------+
                          |
                          v
              +-----------+-----------+
              |                       |
              v                       v
     +--------+--------+    +--------+--------+
     | VILLAGE NOT FULL |    | VILLAGE FULL!   |
     | -> Loop back to  |    | -> Celebration  |
     |    FAMILY HUB    |    | -> Earn horse   |
     +-----------------+    |    collectible   |
                             | -> Contribute   |
                             |    to national  |
                             |    map          |
                             +--------+--------+
                                      |
                                      v
                             +--------+--------+
                             | NATIONAL MAP    |
                             | Family's light  |
                             | joins millions  |
                             | -> New village  |
                             |    unlocks      |
                             | -> Wait for     |
                             |    next sync    |
                             |    moment       |
                             +-----------------+
```

### Rules Specification

**Rule 1: Family Team Formation**
- Input: Player opens the Mini Program, creates or joins a family team via WeChat group link or QR code
- Process: Teams of 2-8 players. Each player self-selects a role: Firekeeper (shake), Lantern Hanger (tap), or Guardian (defend). Roles can be changed anytime. Multiple players can share the same role.
- Output: Family team with assigned roles, standing in their dark virtual village
- Why: Team formation via WeChat group link leverages the existing family group chat, requiring zero new social infrastructure. Self-selected roles respect player agency. [Precedent: Jackbox Games -- players choose their own comfort level]

**Rule 2: Shake to Strike (Firekeeper role -- designed for elderly)**
- Input: Gentle phone shake (low threshold, 2-3 shakes sufficient)
- Process: Each shake "strikes the flint," generating a spark. 3 sparks = 1 flame ready for hanging. Visual: warm sparks fly from the phone with haptic feedback.
- Output: Flame token added to the family's shared pool
- Why: Shaking is the most accessible mobile interaction (proven at 110B Chunwan interactions in 2015). Low threshold ensures elderly users with limited grip strength can participate. [Research Report, Section 2: WeChat 2015 success; Section 6: shake-to-win format]

**Rule 3: Tap to Hang (Lantern Hanger role -- designed for adults)**
- Input: Tap a specific position on the village scene to place a lantern
- Process: Player sees the dark village with marked lantern hooks (glowing dots). Tap a hook + drag a flame from the shared pool to light the lantern. Each lantern illuminates a small area of the village. Some hooks require 2 flames (larger lanterns).
- Output: Lantern lit, village brightness increases, mini-hongbao (0.01-0.88 yuan) awarded
- Why: Slightly more complex than shaking but still single-action. The drag-and-place mechanic gives a satisfying sense of craftsmanship. [Precedent: puzzle placement mechanics in casual games like Merge Mansion]

**Rule 4: Tap to Defend (Guardian role -- designed for youth)**
- Input: Quick taps on Nian beast shadows that appear at the edges of the village
- Process: Every 30-60 seconds, Nian beast shadows creep toward lit lanterns. If not tapped within 3 seconds, the beast extinguishes one lantern. Beasts appear faster as the village gets brighter (escalation). Visual: dramatic red eyes in the darkness, satisfying "poof" when tapped.
- Output: Beast repelled, lanterns protected, bonus sparks earned for the Firekeeper pool
- Why: This role channels the energy of younger players who crave action. The defensive mechanic creates tension without penalizing the whole team severely (only 1 lantern lost per missed beast). [Precedent: Plants vs. Zombies -- defend your territory; whack-a-mole timing mechanic]

**Rule 5: Golden Horse Event (Synchronized with broadcast)**
- Input: During designated Chunwan broadcast moments (4-6 times during the show), the Lucky Horse gallops across all players' screens
- Process: Any family member can tap the horse. It runs across the screen for 5 seconds. Successful catch = golden lantern (worth 5 regular lanterns). Miss = no penalty.
- Output: Golden lantern added to village; family cheers
- Why: Creates shared "event" moments that sync with the live broadcast, driving FOMO and excitement. The generous 5-second window ensures even slower players have a chance. Any family member catching it benefits all, reinforcing cooperation. [Research Report, Recommendation 5: broadcast synchronization; Precedent: WeChat 2015 shake moments]

### Scoring System

| Action | Points | Currency |
|--------|--------|----------|
| Shake (Firekeeper) | 1 spark per shake | Sparks (shared pool) |
| Hang lantern | 10 points per lantern | Family score |
| Defend against Nian | 5 points + 2 bonus sparks | Family score + sparks |
| Catch Golden Horse | 50 points + golden lantern (5x) | Family score + special |
| Complete village | 200 bonus points + horse collectible | Family score + collection |
| AI couplet share | 20 bonus points | Family score |

**Scoring philosophy**: Points are abundant and feel generous. The goal is not to make scoring hard but to make families feel accomplished. The competitive element is at the province level (which province lights up first), not between families directly. [Research Report, Section 6: fairness > surprise]

### Win/Loss Conditions

- **There is no "losing."** Every family that participates lights at least some lanterns. The game is designed so that even minimal participation (a few shakes from grandma) contributes meaningfully.
- **"Winning" is collective.** The "win" moment is when your family completes their village AND when your province completes on the national map.
- **Why no losing**: Research shows fairness is the #1 concern for game show viewers. A family game where grandma "causes the team to lose" would be the opposite of the reunion spirit. Every contribution matters; no contribution causes failure. [Research Report, Section 1: "Fairness > surprise"; Agent prompt Section 1: "Fairness > surprise"]

### Round Structure and Escalation

The game runs in 3 phases aligned with the Chunwan broadcast:

| Phase | Chunwan Timing | Game State | Difficulty | Duration |
|-------|---------------|------------|------------|----------|
| **Phase 1: Kindling** | Early show (8:00-9:30 PM) | Village is dark, first lanterns being lit | Easy: Nian beasts slow, sparks plentiful | ~90 min |
| **Phase 2: Blazing** | Mid show (9:30-11:00 PM) | Village half-lit, golden horses appear more frequently | Medium: Nian beasts faster, 2-flame lanterns appear | ~90 min |
| **Phase 3: Radiance** | Countdown (11:00 PM - midnight) | Race to complete, national map filling up | High: Nian beasts aggressive, but golden horses frequent too | ~60 min |
| **Climax** | Midnight | All lanterns converge into collective fireworks display | N/A -- celebration mode | ~5 min |

Escalation is gentle. The game gets slightly harder but also more rewarding (more golden horse events, bigger hongbao in later phases). The goal is rising excitement, not frustration. [Agent prompt: "Early game (hook), mid game (challenge), end game (climax)"]

---

## 4. Player Flow

### Discovery -> Onboarding -> Core Gameplay -> Climax -> Resolution

**Step 1: Discovery (T+0s)**
- Context: Family is watching Chunwan. A QR code appears on the TV screen during a program transition, or a family member shares a WeChat Mini Program link in the family group chat.
- Action: Player scans QR code or taps the shared link.
- Emotion: Curiosity. "What's this? A game?"

**Step 2: Entry (T+3s)**
- Context: WeChat Mini Program opens instantly (no download, no login -- WeChat identity automatic).
- Screen: A warm, dark village scene with the text: "Your family's village is waiting for light. Invite your family to help!"
- Action: Player taps "Create Family Team" or "Join Family" (via group link already shared).
- Emotion: Intrigue. The dark village is inviting, not intimidating.

**Step 3: Onboarding (T+8s, <20 seconds total)**
- Context: Brief animated tutorial. Three panels, auto-advancing:
  - Panel 1: "Grandpa shakes to make sparks" (animation of phone shaking, sparks flying) -- 5s
  - Panel 2: "Mom taps to hang lanterns" (animation of dragging flame to lantern hook) -- 5s
  - Panel 3: "Kids tap fast to chase away the Nian beast!" (animation of tapping beast shadow) -- 5s
- Action: Player picks their role by tapping one of three large, labeled buttons (with icon + text).
- Emotion: Clarity. "I know exactly what to do. This is simple."
- Design note: Tutorial is skippable for returning players. Role buttons are color-coded and large (minimum 60x60dp tap target). [Research Report, Section 8: accessibility; Agent prompt: "Design for the weakest link"]

**Step 4: Core Gameplay (T+30s onward, repeating loop)**
- Context: The family is in their village. Each member sees the same village from their role's perspective. The Firekeeper sees the spark-generation interface prominently. The Lantern Hanger sees the village map with hooks. The Guardian sees the defensive perimeter.
- Actions: Each player performs their role's action (shake/tap/defend). The village gradually lights up. Every few minutes, a golden horse event triggers.
- Emotion: Flow state. Comfortable repetition with occasional spikes of excitement (Nian beast, golden horse). The village getting brighter provides constant visual progress feedback.

**Step 5: Village Completion (variable timing, ~15-30 min of active play)**
- Context: The last lantern is lit. The village erupts in golden light.
- Screen: Celebration animation. Family avatars appear together in the glowing village. A custom AI-generated spring couplet based on the family's play style appears (e.g., "Swift horse carries the family torch / Ten thousand lanterns greet the spring").
- Action: Player can share the couplet + village screenshot to WeChat Moments.
- Emotion: Pride, togetherness. "We did this as a family."

**Step 6: National Map Contribution (T+completion)**
- Context: Family's completed village light flies upward and joins the national map. Player zooms out to see their province filling with lights from other families.
- Action: Passive viewing. Can explore the map, see province rankings.
- Emotion: Awe, community belonging. "We're part of something huge."

**Step 7: Continued Play (T+completion onward)**
- Context: Family can "adopt" a new, harder village (different regional theme: northern courtyard, southern garden, Sichuan teahouse, etc.) for more collectibles and a new horse variant.
- Action: Optional -- start a new village round, or just spectate the national map.
- Emotion: Satisfying choice: play more for collection depth, or relax and watch.

**Step 8: Midnight Climax (11:59 PM)**
- Context: 60-second countdown synced with the Chunwan broadcast. All families' accumulated lantern energy converts into virtual fireworks.
- Action: Each family member taps rhythmically to "launch" their fireworks. More taps = more fireworks.
- Screen: Split view -- top half shows the national fireworks display (collective), bottom half shows your family's personal fireworks streak.
- Emotion: Exhilaration, shared celebration, tears-of-joy territory. This is the peak emotional moment.

**Step 9: Resolution (Post-midnight)**
- Screen: Summary card: family stats (lanterns lit, beasts defeated, horses caught), province ranking, horse collectibles earned, total hongbao earned, AI-generated family couplet.
- Action: Share summary card to WeChat Moments / family group.
- Emotion: Warm afterglow. Pride in the family's collective achievement.

---

## 5. Interaction Model

### Input Methods

| Role | Primary Input | Fallback Input | Accessibility Note |
|------|--------------|----------------|-------------------|
| Firekeeper (Elder) | Phone shake (accelerometer) | Large "tap here" button for users who cannot shake | Button is always visible; shake is optional enhancement |
| Lantern Hanger (Adult) | Tap + drag on screen | Tap only (auto-place at nearest available hook) | Single-tap mode in accessibility settings |
| Guardian (Youth) | Quick taps on beast targets | Tilt-to-aim + auto-fire option | Targets are large (min 80x80dp); 3-second window is generous |
| Golden Horse (All) | Single tap anywhere on screen | Automatic collection if any family member succeeds | Full-screen tap target -- impossible to miss if you try |

### Platform Support

| Platform | Experience Level | Technical Requirement |
|----------|-----------------|----------------------|
| **WeChat Mini Program** (primary) | Full interactive experience | WeChat 8.0+, iOS 12+ or Android 7+ |
| **Mobile web** (fallback) | Full experience via browser | Any modern mobile browser |
| **Smart TV companion page** | Spectator mode: national map + family progress | Smart TV browser or phone casting to TV |
| **Non-digital** | TV-only viewers enjoy the national map overlay during Chunwan broadcast | No device needed |

### Real-Time vs. Asynchronous

- **Family interactions**: Real-time via WebSocket. Family members see each other's actions reflected immediately (sparks generated by grandpa appear in the Lantern Hanger's flame pool within <500ms).
- **National map**: Near-real-time (5-second update batches). Individual family completions aggregate into province-level data.
- **Golden Horse events**: Server-pushed at synchronized broadcast moments. All families receive the event within a 2-second window.
- **Latency tolerance**: Core gameplay works with up to 2-second latency. Golden Horse has a 5-second window precisely to absorb network variance. [Research Report, Section 7: Taobao benchmark 1.74s first-screen load]

### Spectator Mode for TV-Only Viewers

TV-only viewers (estimated 30-40% of Chunwan audience) see:
- A companion web page (accessed via smart TV browser or a simple URL on their phone) showing the live national map
- Province-level lantern counts updating in real-time
- Highlight moments when provinces "complete" (visual fanfare)
- The midnight fireworks collective display

This ensures the game is entertaining to WATCH without playing. The national map is itself a spectacle. [Agent prompt Anti-Pattern 8.4: "The game must be entertaining to WATCH even for non-participants"]

---

## 6. Multiplayer & Social

### Team Formation

- **Primary method**: Family group chat in WeChat. One person creates the room and shares the link to the family WeChat group. Tap to join. Zero friction.
- **Secondary method**: QR code scan. One phone displays a QR code, others scan it.
- **Solo mode**: A player without family present can join a "stranger family" (random matchmaking) or play solo (all roles available, switching between them).
- **Why WeChat group link**: 90%+ of Chinese families have a WeChat family group. Leveraging this eliminates ALL social friction. [Research Report, Section 3: "Family WeChat groups become real-time commentary channels"]

### Cooperation vs. Competition Balance

| Level | Type | Mechanic |
|-------|------|----------|
| **Within family** | 100% cooperative | All roles contribute to the same village. No individual scores shown during play. Family score only. |
| **Between families** | Friendly competitive | Province-level leaderboard. "Guangdong has lit 2.3 million lanterns!" No individual family is singled out (privacy). |
| **National** | Collective | The national map filling up is the shared goal. "Can all of China light up before midnight?" |

**Design rationale**: Competition between family members would undermine the reunion spirit. Competition between provinces channels regional pride (a powerful, positive motivator in China) without creating interpersonal conflict. The national collective goal gives everyone a shared win condition. [Precedent: Wikipedia fundraising progress bar; cooperative board games like Pandemic]

### Social Sharing Triggers

| Trigger | Shareable Content | Platform |
|---------|------------------|----------|
| Village completion | Village screenshot + AI couplet | WeChat Moments, family group |
| Golden Horse catch | Animated horse catch replay (3-second clip) | WeChat, Douyin |
| Midnight fireworks | Personal fireworks display + family stats | WeChat Moments, Xiaohongshu |
| Post-game summary | Family achievement card (lanterns, rank, collectibles) | WeChat, all platforms |
| Horse collection | Collectible display (show off rare horses) | WeChat, Weibo |

**Share rate target**: 40%+ of completing families share at least one piece of content. [Research Report: Taobao AIGC achieved 80%+ share rate; we target lower because our content is less personalized-photo-based]

### Leaderboards and Visibility

- **Province leaderboard**: Visible to all. Shows total lanterns per province. Updates every 5 seconds. Creates regional pride competition.
- **Family leaderboard**: NOT publicly visible. Each family sees their own stats. No public ranking of families (avoids embarrassment for families with fewer players or lower skill).
- **Why no public family ranking**: Chunwan is about unity, not humiliation. Publicly ranking families would create negative emotions. Province-level aggregation is positive (regional pride) without singling anyone out. [Agent prompt: "Fairness > surprise"]

---

## 7. Cultural Integration

### Deep Integration (Mechanics, Not Skin)

| Cultural Element | Surface-Level (avoided) | Deep Integration (implemented) |
|-----------------|------------------------|-------------------------------|
| **Lanterns** | Lantern graphics as decoration | Lanterns ARE the core mechanic -- lighting them is the entire game. Each lantern type (round, palace, lotus, horse-shaped) has different spark requirements and illumination radius |
| **Nian beast** | Nian beast image on loading screen | Nian beast is the antagonist mechanic -- it creates the tension loop. Without the beast, lanterns are just decoration. With it, lighting becomes an act of protection and courage |
| **Red envelopes** | Cash prize at the end | Micro-hongbao per lantern (instant gratification) + cumulative hongbao for village completion (delayed gratification). The act of earning hongbao IS the gameplay reward, not a separate system |
| **Horse year** | Horse-themed loading screen | The Lucky Horse is a timed gameplay event synced to the broadcast. Catching it requires family coordination. Horse collectibles are the long-arc collection goal |
| **Family reunion** | "Happy reunion!" text at the end | The cooperative team structure IS reunion. You literally cannot complete the game efficiently alone. The game mechanically requires family cooperation, making reunion not a theme but a requirement |
| **Fireworks** | Fireworks animation at midnight | Each family's accumulated lantern energy powers their fireworks contribution. More gameplay = more spectacular fireworks. The collective display is built from millions of individual family contributions |
| **Spring couplets** | Static couplet on screen | AI-generated personalized couplet based on family play style (e.g., a family that defended well gets a courage-themed couplet). Couplet is the shareable trophy |

### Zodiac Theme: Year of the Horse (2026)

The Lucky Horse (Jixiang Ma) is not merely decorative:

1. **Golden Horse Event**: Timed gameplay mechanic synced to the broadcast. The horse gallops across the screen, and catching it is a family-wide reflex challenge worth 5x normal lantern value.

2. **Horse Collectibles**: 12 horse variants (one for each zodiac year's legendary horse from Chinese history) serve as the long-arc collection goal:
   - Matafeiyan (Galloping Horse Treading on a Swallow) -- the 2026 mascot original, based on the Eastern Han bronze from Gansu Wuwei [Research Report, Section 4]
   - Chi Tu (Red Hare, Lu Bu's legendary mount)
   - Zhao Ye Bai (Zhao Yun's white horse)
   - Dilu (Liu Bei's horse that leapt the Tan River)
   - Hanbao Ma (Emperor Qianlong's favorite horse, from Castiglione's paintings)
   - Wu Hua Ma (Five-Flower Horse, from Li Bai's poetry)
   - And 6 more unlockable across the Spring Festival period (7-day collection)

3. **Horse Power-Ups**: Each collected horse variant grants a small passive bonus (e.g., Chi Tu: +10% spark generation; Dilu: Nian beast defense radius +20%). This makes collection functionally meaningful, not just cosmetic. [Agent prompt Section 4.1: "Cultural integration over cultural decoration"]

### Regional Variation

After completing their first village, families can "adopt" villages from different regions:

| Village Theme | Region | Visual Style | Special Mechanic |
|--------------|--------|-------------|-----------------|
| Northern Courtyard (siheyuan) | Beijing/North | Courtyard with kang, paper-cut window decorations | Paper-cut mini-game to earn bonus sparks |
| Water Town (jiangnan) | Jiangnan/South | Canal-side houses, bridges, willow trees | Lanterns float on water; must place before current carries them away |
| Bamboo House | Sichuan/Southwest | Bamboo structure, tea garden, panda silhouettes | Mahjong tile match for bonus lanterns (2-tile simple match, not full mahjong) |
| Yurt Village | Inner Mongolia/Grassland | Ger tents, horse herds, open steppe | Horse racing bonus game (tilt to steer) |
| Ice Lantern City | Northeast/Harbin | Ice sculptures, snow, northern lights | Lanterns are ice lanterns; must keep warm (team shake generates "warmth" meter) |

Each village introduces a small unique mechanic while keeping the core loop (shake/tap/defend) intact. This adds variety for replay without complexity for first-time players. Regional themes are respectful and celebratory, not stereotyping. [Research Report, Section 4: regional variations table]

### Sensitivity Checklist

| Check | Status | Notes |
|-------|--------|-------|
| No political content | PASS | Game is purely cultural celebration |
| No religious content | PASS | No religious symbols or references |
| No ethnic stereotyping | PASS | Regional villages celebrate culture positively; reviewed by cultural consultant recommended |
| No number 4 in prominent positions | PASS | Scoring uses 5/10/20/50/200; no tier or level labeled "4" |
| No white/black color dominance | PASS | Primary palette: red, gold, warm orange, deep blue (night sky). White used only for snow in Ice Lantern village. Black used only for Nian beast (culturally appropriate -- the beast IS dark) |
| No clock imagery | PASS | Countdown uses firework fuse visual, not clock |
| No green hats | PASS | No character wears green headwear |
| All zodiac animals positive | PASS | Horse collectibles presented with historical reverence and admiration |
| UGC moderation plan | PASS | AI couplet generation uses allowlist vocabulary; no free-text user input reaches other players |
| Gambling compliance | PASS | Hongbao amounts are random within range but ALL players receive rewards; no "you lose everything" mechanic; odds disclosed in rules |

---

## 8. Difficulty & Pacing

### Difficulty Curve

```
Difficulty
    ^
    |
 10 |                                              ****  (Midnight rush)
    |                                          ****
  8 |                                      ****
    |                                  ****
  6 |                             *****
    |                        *****
  4 |                  ******
    |            ******
  2 |      ******
    | *****
  0 +----+----+----+----+----+----+----+----+----+--->
    8pm  8:30 9:00 9:30 10:00 10:30 11:00 11:30 12:00
         Phase 1: Kindling    Phase 2: Blazing    Phase 3: Radiance
         (Gentle)             (Engaging)          (Exciting)
```

### Phase Breakdown

**Phase 1: Kindling (8:00 - 9:30 PM) -- "The Hook"**
- Nian beasts: Slow, infrequent (1 per 60 seconds), single lantern threat
- Sparks: Generous (2 shakes = 1 spark)
- Golden Horse: 1 event during this phase
- Feeling: Cozy, exploratory. "Hey, this is fun. Let me shake some more."
- Design goal: Onboard the family. Let grandma get comfortable with shaking. Let the kid discover defending is fun.

**Phase 2: Blazing (9:30 - 11:00 PM) -- "The Challenge"**
- Nian beasts: Medium speed, more frequent (1 per 30 seconds), some attack 2 lanterns
- Sparks: Normal (3 shakes = 1 spark)
- Golden Horse: 2-3 events during this phase
- New mechanic: 2-flame lanterns appear (require more sparks)
- Feeling: Engaged, slightly pressured. "We need more sparks! Grandpa, shake more!"
- Design goal: Create light inter-family banter and cooperation pressure. The family starts strategizing together.

**Phase 3: Radiance (11:00 PM - midnight) -- "The Rush"**
- Nian beasts: Fast, frequent (1 per 15 seconds), some extinguish 2 lanterns
- Sparks: Same as Phase 2 (do NOT make earning harder; increase demand instead)
- Golden Horse: 2-3 events, plus special "countdown horse" at 11:55 PM worth 10x
- New mechanic: "Guang ming" (radiance) chain -- lighting 3 lanterns in 10 seconds triggers a chain reaction lighting 2 nearby lanterns for free
- Feeling: Exciting, urgent. "We need to finish before midnight! Everyone go!"
- Design goal: Maximum engagement for the countdown. The "guang ming" chain reward ensures even struggling families can complete their village.

### Adaptive Difficulty

The game subtly adjusts difficulty based on family performance:
- If a family has < 30% village completion by Phase 2, Nian beast frequency decreases by 20%
- If a family has > 80% completion by Phase 2, Nian beasts become more aggressive to maintain tension
- This is invisible to the player. The goal is to ensure EVERY family can complete their first village by midnight, because the midnight fireworks moment is the emotional payoff everyone deserves.
- Why: "Design for the weakest link." If grandma's family of 2 (her + one grandchild) cannot complete the village, they miss the midnight moment. Adaptive difficulty prevents this without punishing skilled families. [Agent prompt: "Inclusive by default, expert-friendly by option"]

---

## 9. UI/UX Guidelines

### Screen Layout: Main Gameplay (Portrait Orientation)

```
+----------------------------------+
|  [Family Name]    [Lantern: 24/40] |
|  [Phase 2: Blazing]   [Timer]    |
+----------------------------------+
|                                  |
|    .  *  .                       |
|   __|__|__    [Lantern]          |
|  |  HOME  |   .    [Hook]       |
|  |________|  [Lit]    .         |
|       [Lit]    .  [Hook]        |
|  .         [Nian!]              |
|     [Lit]        .   [Hook]     |
|  [Lit]    .  [Lit]              |
|       .         [Lit]           |
|                                  |
+----------------------------------+
| [Spark Pool: 🔥🔥🔥 5/10]       |
| [Your Role: Lantern Hanger]     |
+----------------------------------+
|  [SHAKE]  [HANG]  [DEFEND]      |
|  (switch role buttons, subtle)   |
+----------------------------------+
```

**Key layout principles:**
- Top bar: Family name, progress (lanterns lit / total), phase indicator, timer to next golden horse
- Center: Village scene (80% of screen). This is where all the action happens. Lanterns glow warmly when lit. Dark areas invite illumination.
- Bottom bar: Shared resource pool (sparks), current role indicator, role-switching buttons (small, unobtrusive -- role switching is infrequent)
- Minimum tap target: 60dp x 60dp for all interactive elements. Nian beast targets are 80dp x 80dp minimum.
- Orientation: Portrait only. [Research Report, Section 9: "vertical-screen mobile-first design"; 5.3B vertical-screen Chunwan views]

### Screen Layout: National Map

```
+----------------------------------+
|  NATIONAL LANTERN MAP            |
|  [Families: 12.3M] [Lanterns:   |
|   847M]                          |
+----------------------------------+
|                                  |
|      [China map silhouette]      |
|    Provinces glow by intensity   |
|    of family completions         |
|                                  |
|    [Guangdong: 92%] ★            |
|    [Zhejiang: 87%]               |
|    [Sichuan: 81%]                |
|                                  |
|    Your province: [Beijing 76%]  |
|    Your family: ★ (completed!)   |
|                                  |
+----------------------------------+
| [Back to Village] [Share Map]    |
+----------------------------------+
```

### Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| Chunwan Red | #C41E3A | Primary accent, hongbao, celebration elements |
| Lantern Gold | #FFD700 | Lit lanterns, sparks, golden horse, achievement badges |
| Warm Orange | #FF8C00 | Firelight glow, progress indicators |
| Night Blue | #1A1A3E | Background (dark village), sky |
| Jade Green | #00A86B | Provincial map accents, nature elements |
| Ivory White | #FFFFF0 | Text on dark backgrounds (high contrast) |
| Nian Black | #1C1C1C | Nian beast, shadows (minimal usage, never dominant) |

**Palette rationale**: Red and gold dominate, as culturally appropriate for Spring Festival. Night blue provides contrast for the "lighting up darkness" fantasy. No white or black dominance. [Research Report, Section 8: cultural sensitivity on colors]

### Sound Design Direction

| Event | Sound | Emotional Function |
|-------|-------|-------------------|
| Phone shake (spark) | Crisp "ting" + subtle whoosh | Satisfaction of creation |
| Lantern lit | Warm "fwoosh" + soft chime | Achievement, warmth |
| Nian beast appears | Low rumble + ominous growl | Alert, tension |
| Nian beast repelled | Satisfying "poof" + sparkle | Relief, triumph |
| Golden Horse gallop | Exciting drum beat + horse whinny | Excitement, urgency |
| Golden Horse caught | Triumphant horn + crowd cheer | Celebration, family pride |
| Village completed | Full orchestral swell + fireworks | Pride, accomplishment |
| Midnight fireworks | Ascending whistle + explosion + crowd "ohhh" | Climactic joy |
| Hongbao received | Classic WeChat hongbao "ding" sound | Familiar satisfaction |

**Sound philosophy**: Familiar sounds (WeChat hongbao ding) anchor the experience in known territory. New sounds (horse gallop, Nian growl) create the game's unique identity. All sounds are short (<2 seconds) to avoid interfering with the Chunwan broadcast audio. Volume defaults to 50% and is easily adjustable. An option to mute game sounds (relying on haptic only) is prominently available. [Research Report: dual-screen context means game audio competes with TV audio]

### Accessibility Notes

1. **Large text mode**: All UI text is minimum 16sp by default. "Senior mode" increases to 22sp with simplified layout (fewer on-screen elements).
2. **High contrast mode**: Lit lanterns have bright glowing borders (not just color change). Nian beast targets have pulsing red outlines.
3. **Haptic feedback**: Every successful action triggers haptic feedback (vibration). For deaf users or noisy environments, haptic replaces audio cues entirely.
4. **Shake alternative**: A large, prominent "TAP" button replaces shake for users with mobility limitations. This is not hidden in settings -- it is always visible alongside the shake prompt.
5. **Screen reader support**: All interactive elements have content descriptions. Village state can be read as text ("Your village is 60% lit. 16 lanterns remaining.").
6. **Color-blind safe**: No game information is conveyed by color alone. Lit vs. unlit lanterns differ in brightness, animation (flame flicker), and icon state, not just color.
7. **Auto-play for spectators**: Family members who open the game but do not interact for 60 seconds are shown the village in "spectator mode" with gentle prompts to participate. They are not penalized or removed.

---

## 10. Technical Constraints & Estimates

### Platform Requirements

| Requirement | Specification |
|------------|--------------|
| Primary platform | WeChat Mini Program (main package < 8MB) |
| Minimum OS | iOS 12 / Android 7.0 |
| Minimum device | 2GB RAM, quad-core processor (2018-era budget phone) |
| Network | Functional on 4G (1 Mbps+); graceful degradation on 3G |
| Framework | Canvas 2D rendering (avoid WebGL for maximum compatibility on low-end devices); WebGL optional for enhanced visual effects on capable devices |

### Latency Tolerance

| Interaction | Max Acceptable Latency | Design Mitigation |
|------------|----------------------|-------------------|
| Shake -> Spark | 200ms (client-side, no server round-trip needed) | Spark generation is client-side with server reconciliation |
| Lantern placement | 500ms | Optimistic UI: lantern lights immediately, server confirms asynchronously |
| Nian beast tap | 300ms | Beast targets are client-side rendered; server only tracks score |
| Golden Horse | 5-second window | Generous window absorbs up to 2s network delay |
| Family state sync | 1 second | WebSocket with heartbeat; state reconciles every 1s |
| National map update | 5 seconds | Batch updates; visually smooth via interpolation |

### Estimated Concurrent Users

| Time | Estimated Concurrent Players | Server Requirement |
|------|----------------------------|-------------------|
| Phase 1 (8-9:30 PM) | 50-100M | Warm-up phase; auto-scale |
| Phase 2 (9:30-11 PM) | 100-200M | Peak mid-show engagement |
| Phase 3 (11 PM - midnight) | 200-400M | Peak: countdown rush |
| Midnight moment | 400M+ | Maximum burst: fireworks calculation |

[Reference: WeChat 2015 handled 110B interactions; Taobao 2025 handled zero-failure Chunwan load; Volcano Engine handled 703B interactions for Douyin 2021. These benchmarks prove 400M concurrent is achievable. Research Report, Section 7]

### Server-Side vs. Client-Side Logic Split

| Component | Location | Rationale |
|-----------|----------|-----------|
| Spark generation | Client | Immediate feedback; server reconciles to prevent cheating |
| Lantern state | Hybrid | Client renders optimistically; server is source of truth |
| Nian beast spawning | Server | Prevents client-side manipulation; ensures fair difficulty |
| Golden Horse events | Server-pushed | Synchronized across all clients via broadcast event |
| Scoring | Server | Anti-cheat requirement |
| National map aggregation | Server | Province-level aggregation from family completion events |
| AI couplet generation | Server | LLM inference runs server-side; client receives text |
| Hongbao distribution | Server | Financial transaction requires server authority |

### Implementation Effort Estimate

Note: As per my role, I design the experience, not the code. These are rough directional estimates for the team lead.

| Component | Estimated Effort | Notes |
|-----------|-----------------|-------|
| Core gameplay (shake/tap/defend) | Medium | Proven mechanics, standard canvas rendering |
| Village rendering + animation | Medium-High | 5 regional village themes; lantern lighting effects |
| Family team system | Medium | WebSocket room management; WeChat group integration |
| Golden Horse sync events | Medium | Server-push timing; broadcast coordination API |
| National map | Medium | Province-level aggregation; map visualization |
| AI couplet generation | Low-Medium | Server-side LLM call; template + customization |
| Hongbao system | Medium | Financial integration; compliance requirements |
| Horse collectible system | Low | Static asset management; unlock logic |
| Accessibility features | Medium | Senior mode, haptic, screen reader, alternatives |
| Load testing for 400M concurrent | High | Infrastructure engineering challenge |

---

## 11. Risk Analysis

### Risk 1: Elderly Users Cannot Participate Meaningfully

- **What could go wrong**: Grandma opens the game, is confused by the interface, puts her phone down. The game fails its core promise of multi-generational cooperation.
- **Probability**: Medium-High (elderly UI adoption is the #1 challenge)
- **Impact**: Critical (undermines the entire USP)
- **Mitigation**:
  - The Firekeeper (shake) role has the absolute minimum complexity: shake phone, see sparks. No screen reading required.
  - Fallback: large TAP button always visible for those who cannot shake.
  - The 20-second visual tutorial uses animation, not text.
  - A younger family member can "demo" by shaking grandma's phone once to show her.
  - Adaptive difficulty ensures even minimal contribution from grandma still leads to village completion.
- **Playtesting question**: "Can a 75-year-old who has never played a phone game generate 10 sparks within 2 minutes of opening the app?"

### Risk 2: Server Overload at Midnight

- **What could go wrong**: 400M+ concurrent users crash the server during the midnight fireworks moment, ruining the emotional climax.
- **Probability**: Low-Medium (proven infrastructure exists, but our specific implementation is new)
- **Impact**: Critical (the midnight moment IS the game)
- **Mitigation**:
  - Fireworks calculation is pre-computed from accumulated lantern data (not real-time computation at midnight)
  - Client-side rendering of fireworks from pre-distributed animation assets
  - Server only needs to push a single "launch" event + per-family score payload
  - Load testing must simulate 500M concurrent (25% headroom)
  - Graceful degradation: if server connection drops, client plays local fireworks animation using cached family data
- **Playtesting question**: "What happens if a player's connection drops at 11:59 PM? Do they still see fireworks?"

### Risk 3: Game Is Too Simple / Boring for Young Users

- **What could go wrong**: Youth players (15-29) find the shake/tap/defend loop too basic and lose interest after 5 minutes.
- **Probability**: Medium
- **Impact**: Medium (young users are the social sharing engine; losing them reduces virality)
- **Mitigation**:
  - Guardian (defend) role is designed with increasing difficulty to maintain challenge for skilled players
  - Horse collectible system adds depth layer (12 variants, passive bonuses, historical lore)
  - Regional village themes provide visual variety and new mini-mechanics
  - Province competition on the national map gives competitive players a macro-level goal
  - Social sharing features (animated clips, custom couplets) appeal to content-creation culture
  - The game does NOT need to be a 4-hour engagement for youth; even 20 minutes of engaged play that produces 3 shareable moments is a success
- **Playtesting question**: "After playing for 15 minutes, does a 20-year-old want to share their horse catch clip on Douyin?"

### Risk 4: Cultural Sensitivity Violation

- **What could go wrong**: A regional village theme, AI-generated couplet, or game element is perceived as culturally insensitive or politically inappropriate.
- **Probability**: Low (design is conservative and celebrates rather than satirizes)
- **Impact**: Very High (social media backlash could be instantaneous and devastating)
- **Mitigation**:
  - AI couplet generation uses an allowlist vocabulary (no free-text generation that could produce offensive content)
  - Regional village themes are reviewed by cultural consultants from each region
  - No UGC content reaches other players (no user-generated text/images visible to others)
  - Sensitivity checklist (Section 7) is applied to all visual and textual assets
  - Pre-launch review by CMG content compliance team (mandatory for any Chunwan-associated product)
- **Playtesting question**: "Show each regional village to 5 people from that region. Does anyone feel misrepresented?"

### Risk 5: Hongbao Financial Compliance

- **What could go wrong**: The random hongbao amounts or collection mechanics are classified as gambling under Chinese regulations, triggering legal issues.
- **Probability**: Low-Medium
- **Impact**: High (regulatory action)
- **Mitigation**:
  - All hongbao are guaranteed rewards (no "you might get nothing" mechanic)
  - Amount ranges are disclosed in game rules
  - No secondary market for in-game items (horse collectibles are non-tradeable)
  - Financial integration through established WeChat Pay / Alipay channels with existing regulatory compliance
  - Legal review before launch (mandatory)

### Risk 6: Broadcast Synchronization Failure

- **What could go wrong**: Golden Horse events are mistimed relative to the live broadcast due to latency differences between TV signal, streaming platforms, and CDN regions.
- **Probability**: Medium
- **Impact**: Medium (unfair timing for some users; breaks the "shared moment" illusion)
- **Mitigation**:
  - 5-second activation windows (not precise-second triggers)
  - Events are triggered by server clock, not broadcast signal (pre-scheduled times agreed with CMG broadcast team)
  - Buffer: event activates 2 seconds BEFORE the broadcast moment, ensuring even delayed streams see it in time
  - If broadcast runs ahead/behind schedule, events can be adjusted server-side in real-time by operations team
- [Research Report, Recommendation 5: "use windows (30-second activation periods) rather than precise-second synchronization"]

---

## 12. References

### Real-World Game Formats Cited as Precedents

| Precedent | Mechanic Borrowed | How We Transform It |
|-----------|------------------|---------------------|
| **WeChat 2015 Shake-to-Win** [Research Report, S2] | Phone shake as primary interaction | We keep shake but assign it to a specific role (Firekeeper) rather than as the entire game. Shake produces sparks that feed into a cooperative system, not individual prizes. |
| **Alipay Fu Collection (2016-2025)** [Research Report, S2, S5] | Collectible card mechanics, annual tradition | We create horse collectibles (12 variants) as the long-arc collection layer. Unlike Fu cards, our collectibles have gameplay effects (passive bonuses), not just cosmetic value. |
| **Jackbox Games** | Self-selected roles, mixed-skill group play | Each family member picks their comfort level (easy shake, medium tap, hard defend). No one is forced into a role they cannot handle. |
| **Fall Guys team rounds** | Cooperative team competition | Families cooperate internally but compete at province level. The "team of strangers" cooperation mechanic is borrowed for solo players. |
| **Plants vs. Zombies** | Defend-your-territory mechanic | Guardian role defends lanterns from Nian beasts. The tower-defense feel creates tension without requiring complex strategy. |
| **Pandemic (board game)** | Cooperative game where everyone wins or loses together | No individual losing. The whole family succeeds or falls short together. Shared victory is the design goal. |
| **Wikipedia fundraising bar** | Collective progress visible to all | The national map is a massive collective progress bar. Each family's contribution visibly adds to the whole. |
| **Taobao AIGC "Cloud Participation" 2025** [Research Report, S5] | Personalized shareable content | AI-generated spring couplet as the shareable trophy. Unlike Taobao's photo integration, ours is text-based (lower bandwidth, higher cultural value). |

### Spring Festival Gala Interactive History References

- WeChat 2015: 110B shake interactions, 2M bank cards bound [Research Report, S2]
- Alipay Fu Collection: 900M+ cumulative users over 10 years, 29 card sets in 2025 [Research Report, S5]
- Baidu 2019: Cautionary tale -- 2% retention despite 10B yuan spend [Research Report, S5]
- Bilibili 2025: 100M viewers, 83% under 30, but danmu controversy [Research Report, S5]
- Taobao 2025: 80%+ AIGC share rate, 30 FPS on low-end devices [Research Report, S5, S7]
- Doubao/Volcano Engine 2026: First AI cloud partner, tech-gift paradigm [Research Report, S5]

### Research Report Inputs

- Primary research input: `/mnt/nvme0n1/Projects/agent-orchestrator/cultural-researcher/spring-festival-gala-mini-game-research.md` (CER-001, v1.0, 2026-02-16)
- Key sections referenced: S2 (Chunwan History), S3 (Audience Analysis), S4 (Cultural Context), S5 (Competitive Analysis), S6 (Game Format Precedents), S7 (Platform & Technical), S8 (Cultural Sensitivity), S9 (Trend Analysis), S10 (Recommendations)
- All 5 recommendations from the research report were incorporated:
  1. "Family Living Room" cooperative game -> Core team mechanic (Rec 1)
  2. Collectible + instant reward dual loop -> Hongbao + horse collection (Rec 2)
  3. AI as enhancement, not core -> AI couplet generation at end, not gating gameplay (Rec 3)
  4. 7-day holiday period -> Regional village unlocks extend beyond NYE (Rec 4)
  5. Broadcast synchronization -> Golden Horse events synced to Chunwan moments (Rec 5)

---

## Appendix A: Playtesting Criteria

The following questions must be answered "yes" during user testing before launch:

### Accessibility
1. Can a 75-year-old generate 10 sparks within 2 minutes using only the shake / tap fallback?
2. Can a player with color blindness distinguish lit from unlit lanterns?
3. Can a screen reader user understand village completion percentage?

### Fun Factor
4. Do families laugh or shout during Golden Horse events?
5. Do players want to play a second village after completing the first?
6. Does the midnight fireworks moment produce audible "ooh" reactions?
7. After losing a lantern to the Nian beast, do players feel motivated to defend harder (not frustrated)?

### Social
8. Do 40%+ of completing families share at least one piece of content?
9. Do family WeChat groups have active commentary about the game during Chunwan?
10. Can a family member who joins 30 minutes late catch up and contribute meaningfully?

### Technical
11. Does the game maintain 30 FPS on a 2018-era budget Android phone?
12. Does the game load in under 3 seconds on 4G?
13. Do Golden Horse events appear within 2 seconds across all connected family members?
14. If connection drops for 10 seconds, does the game recover without data loss?

---

## Appendix B: Extended Play -- 7-Day Holiday Content

For families who complete the NYE experience and want to continue during the Spring Festival holiday:

| Day | Content | Unlock Condition |
|-----|---------|-----------------|
| Day 1 (NYE) | First village + midnight fireworks | Game entry |
| Day 2 | Northern Courtyard village | Complete Day 1 village |
| Day 3 | Water Town village + new horse collectible | Complete any 2 villages |
| Day 4 | Bamboo House village | Complete any 3 villages |
| Day 5 | Yurt Village + new horse collectible | Complete any 4 villages |
| Day 6 | Ice Lantern City (hardest) | Complete any 5 villages |
| Day 7 (Lantern Festival) | Grand Finale: All villages merge into one mega-village | Complete all 6 villages |

Daily login rewards: 1 free horse collectible attempt per day. Streak bonus for 7 consecutive days: guaranteed rare horse variant.

This extends the experience from a single evening to the full holiday period, addressing the retention gap identified in the research report (Baidu 2019: 2% retention; Kuaishou 2020: DAU collapse post-event). [Research Report, Recommendation 4]

---

## Appendix C: Evaluation Checklist (Self-Assessment)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | GDD contains all 12 sections | PASS | Sections 1-12 present |
| 2 | Core loop is diagrammed | PASS | ASCII diagram in Section 3 |
| 3 | >= 3 real-world precedents cited with explanation | PASS | 8 precedents in Section 12 (WeChat, Alipay, Jackbox, Fall Guys, PvZ, Pandemic, Wikipedia, Taobao AIGC) |
| 4 | >= 5 cultural elements with mechanical integration | PASS | 7 elements in Section 7 (lanterns, Nian beast, hongbao, horse, reunion, fireworks, couplets) |
| 5 | >= 3 "fun moments" explicitly defined | PASS | 3 moments in Section 2 ("We did it together!", "The horse is coming!", "Look, that's our light!") |
| 6 | Rules can be explained in 60 seconds | PASS | Core rules: "Shake to make sparks. Tap to hang lanterns. Tap fast to chase away monsters. Light up your village as a family before midnight." (12 seconds) |
| 7 | Game is playable by ages 6-80 | PASS | Firekeeper role for elderly (shake/tap), Guardian for youth (reflex), Lantern Hanger for adults (placement). Accessibility features in Section 9. |
| 8 | Risk analysis includes >= 3 risks with mitigations | PASS | 6 risks with detailed mitigations in Section 11 |
| 9 | No culturally insensitive content | PASS | Sensitivity checklist in Section 7 |
| 10 | slot-output.yaml produced | See separate file | `game-designer/slot-output.yaml` |
