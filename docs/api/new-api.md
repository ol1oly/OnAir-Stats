# New API Documentation

The NHL has surprised us all with a new API, so that means a new file to track all the parts of it people have discovered so far.

`https://api-web.nhle.com/v1/`
# Notes

`TEAM_ABBR` is shorthand for the team abbreviation, using the 3 letter ones (WSH, CGY, LAK, etc)

`SEASON_ID` is code for the 8 character season id in the format `<seasonStartYear><seasonEndYear>` e.g. for the 23-24 season: `20232024`

`GAME_ID` has so far remained the same as before, a combination of season year and a unique id element

# Endpoint Tables



# Schedule endpoints

`GET https://api-web.nhle.com/v1/schedule/now` | Gets schedule of games for today (redirects to the corret YYYY-MM-DD format)

<details>
    <summary>click for example (truncated)</summary>

```json
// GET https://api-web.nhle.com/v1/schedule/now 

{
  "nextStartDate": "2023-09-30",
  "previousStartDate": "2023-06-10",
  "gameWeek": [
    {
      "date": "2023-09-23",
      "dayAbbrev": "SAT",
      "numberOfGames": 3,
      "games": [
        {
          "id": 2023010001,
          "season": 20232024,
          "gameType": 1,
          "venue": "Rod Laver Arena",
          "neutralSite": true,
          "startTimeUTC": "2023-09-23T04:05:00Z",
          "easternUTCOffset": "-04:00",
          "venueUTCOffset": "+10:00",
          "venueTimezone": "Australia/Melbourne",
          "gameState": "FINAL",
          "gameScheduleState": "OK",
          "tvBroadcasts": [
            {
              "id": 282,
              "market": "N",
              "countryCode": "CA",
              "network": "SN"
            },
            {
              "id": 324,
              "market": "N",
              "countryCode": "US",
              "network": "NHLN"
            },
            {
              "id": 329,
              "market": "N",
              "countryCode": "US",
              "network": "ESPN+"
            }
          ],
          "awayTeam": {
            "id": 26,
            "city": "Los Angeles",
            "abbrev": "LAK",
            "logo": "https://assets.nhle.com/logos/nhl/svg/LAK_light.svg",
            "awaySplitSquad": true,
            "score": 3
          },
          "homeTeam": {
            "id": 53,
            "city": "Arizona",
            "abbrev": "ARI",
            "logo": "https://assets.nhle.com/logos/nhl/svg/ARI_light.svg",
            "homeSplitSquad": true,
            "score": 5
          },
          "gameOutcome": {
            "lastPeriodType": "REG"
          },
          "winningGoalie": {
            "playerId": 8478971,
            "firstInitial": "C.",
            "lastName": "Ingram"
          },
          "winningGoalScorer": {
            "playerId": 8483431,
            "firstInitial": "L.",
            "lastName": "Cooley"
          },
          "specialEvent": "Global Series",
          "gameCenterLink": "/gamecenter/lak-vs-ari/2023/09/23/2023010001"
        },
      ]
    }
  ],
  "oddsPartners": [
    {
      "partnerId": 1,
      "country": "CA",
      "name": "BET365",
      "imageUrl": "https://assets.nhle.com/betting_partner/bet365.svg",
      "siteUrl": "https://www.on.bet365.ca/olp/nhl",
      "bgColor": "#086D51",
      "textColor": "#FFFFFF",
      "accentColor": "#FDDE14"
    },
    {
      "partnerId": 2,
      "country": "SE",
      "name": "Unibet",
      "imageUrl": "https://assets.nhle.com/betting_partner/unibet.svg",
      "siteUrl": "https://www.unibet.se/betting/sports/filter/ice_hockey/nhl/all/matches",
      "bgColor": "#000000",
      "textColor": "#FFFFFF",
      "accentColor": "#3AAA35"
    },
    {
      "partnerId": 3,
      "country": "CZ",
      "name": "Tipsport",
      "imageUrl": "https://assets.nhle.com/betting_partner/tipsport.svg",
      "siteUrl": "https://www.tipsport.cz/PartnerRedirectAction.do?pid=16961&sid=20360&bid=34954&tid=11268",
      "bgColor": "#2497F2",
      "textColor": "#FFFFFF",
      "accentColor": "#FFFFFF"
    },
    {
      "partnerId": 3,
      "country": "SK",
      "name": "Tipsport",
      "imageUrl": "https://assets.nhle.com/betting_partner/tipsport.svg",
      "siteUrl": "https://www.tipsport.sk/PartnerRedirectAction.do?pid=6823&sid=9018&bid=23079&tid=8475",
      "bgColor": "#2497F2",
      "textColor": "#FFFFFF",
      "accentColor": "#FFFFFF"
    },
    {
      "partnerId": 4,
      "country": "DE",
      "name": "Interwetten",
      "imageUrl": "https://assets.nhle.com/betting_partner/interwetten.svg",
      "siteUrl": "https://www.interwetten.de/de/content/sportsbook/promotions/nhlbonus?utm_source=coop&utm_medium=9111_NHL_de&utm_campaign=NHL_NKB&utm_content=lang_de&utm_term=skin)",
      "bgColor": "#FFD200",
      "textColor": "#121212",
      "accentColor": "#000000"
    },
    {
      "partnerId": 5,
      "country": "RU",
      "name": "Liga Stavok",
      "imageUrl": "https://assets.nhle.com/betting_partner/ligastavok.svg",
      "bgColor": "#007354",
      "textColor": "#FFFFFF",
      "accentColor": "#FFEB00"
    },
    {
      "partnerId": 6,
      "country": "FI",
      "name": "Veikkaus",
      "imageUrl": "https://assets.nhle.com/betting_partner/veikkaus.svg",
      "siteUrl": "https://www.veikkaus.fi/fi/vedonlyonti/pitkaveto?t=3-2-1_NHL",
      "bgColor": "#0025F5",
      "textColor": "#FFFFFF",
      "accentColor": "#FFFFFF"
    },
    {
      "partnerId": 8,
      "country": "US",
      "name": "Sportradar",
      "imageUrl": "https://assets.nhle.com/betting_partner/sportsradar.svg",
      "siteUrl": "https://sportradar.com",
      "bgColor": "#000000",
      "textColor": "#FFFFFF",
      "accentColor": "#E6E6E6"
    }
  ],
  "preSeasonStartDate": "2023-09-23",
  "regularSeasonStartDate": "2023-10-10",
  "regularSeasonEndDate": "2024-04-18",
  "playoffEndDate": "2024-06-18",
  "numberOfGames": 55
}

```

</details>

<br />

[back to top](#endpoint-tables)

`GET https://api-web.nhle.com/v1/schedule/2023-09-23` | Gets schedule of games for specified date
<details>
    <summary>click for example</summary>

```json
// GET https://api-web.nhle.com/v1/schedule/2018-09-01

{
  "nextStartDate": "2018-09-15",
  "previousStartDate": "2018-06-02",
  "gameWeek": [
    {
      "date": "2018-09-01",
      "dayAbbrev": "SAT",
      "numberOfGames": 0,
      "games": []
    },
    {
      "date": "2018-09-02",
      "dayAbbrev": "SUN",
      "numberOfGames": 0,
      "games": []
    },
    {
      "date": "2018-09-03",
      "dayAbbrev": "MON",
      "numberOfGames": 0,
      "games": []
    },
    {
      "date": "2018-09-04",
      "dayAbbrev": "TUE",
      "numberOfGames": 0,
      "games": []
    },
    {
      "date": "2018-09-05",
      "dayAbbrev": "WED",
      "numberOfGames": 0,
      "games": []
    },
    {
      "date": "2018-09-06",
      "dayAbbrev": "THU",
      "numberOfGames": 0,
      "games": []
    },
    {
      "date": "2018-09-07",
      "dayAbbrev": "FRI",
      "numberOfGames": 0,
      "games": []
    }
  ],
  "preSeasonStartDate": "2018-09-15",
  "regularSeasonStartDate": "2018-10-03",
  "regularSeasonEndDate": "2019-04-06",
  "playoffEndDate": "2019-06-12",
  "numberOfGames": 0
}
```
</details>

<br />

`GET https://api-web.nhle.com/v1/club-schedule-season/TEAM_ABBR/now` | gets the full season schedule for the specified team

<details>
    <summary>click for example (truncated)</summary>

```json
// GET https://api-web.nhle.com/v1/club-schedule-season/WSH/now

{
  "previousSeason": 20222023,
  "currentSeason": 20232024,
  "clubTimezone": "US/Eastern",
  "clubUTCOffset": "-04:00",
  "games": [
    {
      "id": 2023010006,
      "season": 20232024,
      "gameType": 1,
      "gameDate": "2023-09-24",
      "venue": "Capital One Arena",
      "neutralSite": false,
      "startTimeUTC": "2023-09-24T18:00:00Z",
      "easternUTCOffset": "-04:00",
      "venueUTCOffset": "-04:00",
      "venueTimezone": "US/Eastern",
      "gameState": "FUT",
      "gameScheduleState": "OK",
      "tvBroadcasts": [
        {
          "id": 324,
          "market": "N",
          "countryCode": "US",
          "network": "NHLN"
        },
        {
          "id": 517,
          "market": "H",
          "countryCode": "US",
          "network": "MNMT"
        }
      ],
      "awayTeam": {
        "id": 7,
        "city": "Buffalo",
        "abbrev": "BUF",
        "logo": "https://assets.nhle.com/logos/nhl/svg/BUF_light.svg",
        "awaySplitSquad": false
      },
      "homeTeam": {
        "id": 15,
        "city": "Washington",
        "abbrev": "WSH",
        "logo": "https://assets.nhle.com/logos/nhl/svg/WSH_light.svg",
        "homeSplitSquad": false,
        "hotelLink": "https://www.hilton.com/en/?WT.mc_id&#x3D;zJWDM0US1MB2OLQ3LocalPartner4DM_Sports_Jun5Coop_Monumental_Capitals_Schedule6MULTIBR7NEHub8i85535",
        "hotelDesc": "Stay With Hilton"
      },
      "ticketsLink": "https://www.ticketmaster.com/event/15005EDCF19B50DD?brand=capitals&artistid=806039&wt.mc_id=NHL_TEAM_WSH_SINGLE_GAME_TICKETS_PAGE_PR1&utm_source=NHL.com&utm_medium=client&utm_campaign=NHL_TEAM_WSH&utm_content=SINGLE_GAME_TICKETS_PAGE_PR1",
      "gameCenterLink": "/gamecenter/buf-vs-wsh/2023/09/24/2023010006"
    },
    {
      "id": 2023010042,
      "season": 20232024,
      "gameType": 1,
      "gameDate": "2023-09-28",
      "venue": "Capital One Arena",
      "neutralSite": false,
      "startTimeUTC": "2023-09-28T23:00:00Z",
      "easternUTCOffset": "-04:00",
      "venueUTCOffset": "-04:00",
      "venueTimezone": "US/Eastern",
      "gameState": "FUT",
      "gameScheduleState": "OK",
      "tvBroadcasts": [
        {
          "id": 324,
          "market": "N",
          "countryCode": "US",
          "network": "NHLN"
        },
        {
          "id": 517,
          "market": "H",
          "countryCode": "US",
          "network": "MNMT"
        }
      ],
      "awayTeam": {
        "id": 17,
        "city": "Detroit",
        "abbrev": "DET",
        "logo": "https://assets.nhle.com/logos/nhl/svg/DET_light.svg",
        "awaySplitSquad": false
      },
      "homeTeam": {
        "id": 15,
        "city": "Washington",
        "abbrev": "WSH",
        "logo": "https://assets.nhle.com/logos/nhl/svg/WSH_light.svg",
        "homeSplitSquad": false,
        "hotelLink": "https://www.hilton.com/en/?WT.mc_id&#x3D;zJWDM0US1MB2OLQ3LocalPartner4DM_Sports_Jun5Coop_Monumental_Capitals_Schedule6MULTIBR7NEHub8i85536",
        "hotelDesc": "Stay With Hilton"
      },
      "ticketsLink": "https://www.ticketmaster.com/event/15005EDCF19C50DF?brand=capitals&artistid=806039&wt.mc_id=NHL_TEAM_WSH_SINGLE_GAME_TICKETS_PAGE_PR2&utm_source=NHL.com&utm_medium=client&utm_campaign=NHL_TEAM_WSH&utm_content=SINGLE_GAME_TICKETS_PAGE_PR2",
      "gameCenterLink": "/gamecenter/det-vs-wsh/2023/09/28/2023010042"
    },
    
  ]
}
```

</details>

<br />

[back to top](#endpoint-tables)

`GET https://api-web.nhle.com/v1/club-schedule/TEAM_ABBR/week/now` | ADD description

<details>
    <summary>click for example</summary>

```json
// GET https://api-web.nhle.com/v1/schedule/2018-01-01

{
  "nextStartDate": "2018-01-08",
  "previousStartDate": "2017-12-25",
  "gameWeek": [
    {
      "date": "2018-01-01",
      "dayAbbrev": "MON",
      "numberOfGames": 1,
      "games": [
        {
          "id": 2017020601,
          "season": 20172018,
          "gameType": 2,
          "venue": "Citi Field",
          "neutralSite": true,
          "startTimeUTC": "2018-01-01T18:00:00Z",
          "easternUTCOffset": "-05:00",
          "venueUTCOffset": "-05:00",
          "venueTimezone": "America/New_York",
          "gameState": "OFF",
          "gameScheduleState": "OK",
          "tvBroadcasts": [
            {
              "id": 29,
              "market": "N",
              "countryCode": "US",
              "network": "NBC"
            },
            {
              "id": 281,
              "market": "N",
              "countryCode": "CA",
              "network": "TVAS"
            },
            {
              "id": 282,
              "market": "N",
              "countryCode": "CA",
              "network": "SN"
            }
          ],
          "awayTeam": {
            "id": 3,
            "city": "New York",
            "abbrev": "NYR",
            "logo": "https://assets.nhle.com/logos/nhl/svg/NYR_light.svg",
            "awaySplitSquad": false,
            "score": 3
          },
          "homeTeam": {
            "id": 7,
            "city": "Buffalo",
            "abbrev": "BUF",
            "logo": "https://assets.nhle.com/logos/nhl/svg/BUF_20102011-20192020_light.svg",
            "homeSplitSquad": false,
            "score": 2
          },
          "gameOutcome": {
            "lastPeriodType": "OT"
          },
          "specialEvent": "Winter Classic",
          "gameCenterLink": "/gamecenter/nyr-vs-buf/2018/01/01/2017020601"
        }
      ]
    },
    {
      "date": "2018-01-02",
      "dayAbbrev": "TUE",
      "numberOfGames": 12,
      "games": [
        {
          "id": 2017020602,
          "season": 20172018,
          "gameType": 2,
          "venue": "Air Canada Centre",
          "neutralSite": false,
          "startTimeUTC": "2018-01-03T00:00:00Z",
          "easternUTCOffset": "-05:00",
          "venueUTCOffset": "-05:00",
          "venueTimezone": "America/Toronto",
          "gameState": "OFF",
          "gameScheduleState": "OK",
          "tvBroadcasts": [
            {
              "id": 38,
              "market": "A",
              "countryCode": "US",
              "network": "SUN"
            },
            {
              "id": 281,
              "market": "N",
              "countryCode": "CA",
              "network": "TVAS"
            },
            {
              "id": 288,
              "market": "H",
              "countryCode": "CA",
              "network": "SNO"
            }
          ],
          "awayTeam": {
            "id": 14,
            "city": "Tampa Bay",
            "abbrev": "TBL",
            "logo": "https://assets.nhle.com/logos/nhl/svg/TBL_light.svg",
            "awaySplitSquad": false,
            "score": 2
          },
          "homeTeam": {
            "id": 10,
            "city": "Toronto",
            "abbrev": "TOR",
            "logo": "https://assets.nhle.com/logos/nhl/svg/TOR_light.svg",
            "homeSplitSquad": false,
            "score": 0
          },
          "gameOutcome": {
            "lastPeriodType": "REG"
          },
          "gameCenterLink": "/gamecenter/tbl-vs-tor/2018/01/02/2017020602"
        },
        {
          "id": 2017020603,
          "season": 20172018,
          "gameType": 2,
          "venue": "Barclays Center",
          "neutralSite": false,
          "startTimeUTC": "2018-01-03T00:00:00Z",
          "easternUTCOffset": "-05:00",
          "venueUTCOffset": "-05:00",
          "venueTimezone": "America/New_York",
          "gameState": "OFF",
          "gameScheduleState": "OK",
          "tvBroadcasts": [
            {
              "id": 31,
              "market": "A",
              "countryCode": "US",
              "network": "NESN"
            },
            {
              "id": 282,
              "market": "N",
              "countryCode": "CA",
              "network": "SN"
            },
            {
              "id": 299,
              "market": "H",
              "countryCode": "US",
              "network": "MSG+"
            }
          ],
          "awayTeam": {
            "id": 6,
            "city": "Boston",
            "abbrev": "BOS",
            "logo": "https://assets.nhle.com/logos/nhl/svg/BOS_20082009-20222023_light.svg",
            "awaySplitSquad": false,
            "score": 5
          },
          "homeTeam": {
            "id": 2,
            "city": "New York",
            "abbrev": "NYI",
            "logo": "https://assets.nhle.com/logos/nhl/svg/NYI_light.svg",
            "homeSplitSquad": false,
            "score": 1
          },
          "gameOutcome": {
            "lastPeriodType": "REG"
          },
          "gameCenterLink": "/gamecenter/bos-vs-nyi/2018/01/02/2017020603"
        },
        {
          "id": 2017020604,
          "season": 20172018,
          "gameType": 2,
          "venue": "Wells Fargo Center",
          "neutralSite": false,
          "startTimeUTC": "2018-01-03T00:00:00Z",
          "easternUTCOffset": "-05:00",
          "venueUTCOffset": "-05:00",
          "venueTimezone": "US/Eastern",
          "gameState": "OFF",
          "gameScheduleState": "OK",
          "tvBroadcasts": [
            {
              "id": 241,
              "market": "N",
              "countryCode": "US",
              "network": "NBCSN"
            }
          ],
          "awayTeam": {
            "id": 5,
            "city": "Pittsburgh",
            "abbrev": "PIT",
            "logo": "https://assets.nhle.com/logos/nhl/svg/PIT_light.svg",
            "awaySplitSquad": false,
            "score": 5
          },
          "homeTeam": {
            "id": 4,
            "city": "Philadelphia",
            "abbrev": "PHI",
            "logo": "https://assets.nhle.com/logos/nhl/svg/PHI_19992000-20222023_light.svg",
            "homeSplitSquad": false,
            "score": 1
          },
          "gameOutcome": {
            "lastPeriodType": "REG"
          },
          "gameCenterLink": "/gamecenter/pit-vs-phi/2018/01/02/2017020604"
        },
      ]
    }
  ],
  "preSeasonStartDate": "2017-09-16",
  "regularSeasonStartDate": "2017-10-04",
  "regularSeasonEndDate": "2018-04-08",
  "playoffEndDate": "2018-06-07",
  "numberOfGames": 50
}
```
</details>

<br />

[back to top](#endpoint-tables)

`GET https://api-web.nhle.com/v1/club-schedule/TEAM_ABBR/month/now` | ADD description

# Standings

`GET https://api-web.nhle.com/v1/standings/now` | Gets standings as of the current date

`GET https://api-web.nhle.com/v1/standings-season` | ADD description

# Stats

`GET https://api-web.nhle.com/v1/club-stats-season/TEAM_ABBR` | Team stats by season

`GET https://api-web.nhle.com/v1/player/PLAYER_ID/landing` | Player specific stats

`GET https://api.nhle.com/stats/rest/en/` | Base stats URL

`/config` | Stats configuration options. For each stat option and report type, this endpoint describes the default configuration of the columns, filters and sorting. <br>
`/franchise?` | Franchise info <br>
`/country?` | Country info <br>
`/season?` | Season info <br>
`/draft?` | Draft info <br>	

## Skater Stats

`GET https://api.nhle.com/stats/rest/en/skater` | Base end point

### Report types: <br>
 `/summary?`<br>
 `/bios?`<br>
 `/faceoffpercentages?`<br>
 `/faceoffwins?`<br>
 `/goalsForAgainst?`<br>
 `/realtime?`<br>
 `/penalties?`<br>
 `/penaltykill?`<br>
 `/penaltyShots?`<br>
 `/powerplay?`<br>
 `/puckPossessions?`<br>
 `/summaryshooting?`<br>
 `/percentages?`<br>
 `/scoringRates?`<br>
 `/scoringpergame?`<br>
 `/shootout?`<br>
 `/shottype?`<br>
 `/timeonice?`<br>
## Goalie Stats

`GET https://api.nhle.com/stats/rest/en/goalie` | Base end point
### Report types: <br>
 `/summary?`<br>
 `/advanced?`<br>
 `/bios?`<br>
 `/daysrest?`<br>
 `/penaltyShots?`<br>
 `/savesByStrength?`<br>
 `/shootout?`<br>
 `/startedVsRelieved?`<br>

## Team Stats
`GET https://api.nhle.com/stats/rest/en/team` | Base end point
### Report types: <br>
 `/summary?`<br>
 `/faceoffpercentages?`<br>
 `/daysbetweengames?`<br>
 `/faceoffwins?`<br>
 `/goalsagainstbystrength?`<br>
 `/goalsbyperiod?`<br>
 `/goalsforbystrength?`<br>
 `/leadingtrailing?`<br>
 `/realtime?`<br>
 `/outshootoutshotby?`<br>
 `/penalties?`<br>
 `/penaltykill?`<br>
 `/penaltykilltime?`<br>
 `/powerplay?`<br>
 `/powerplaytime?`<br>
 `/summaryshooting?`<br>
 `/percentages?`<br>
 `/scoretrailfirst?`<br>
 `/shootout?`<br>
 `/shottype?`<br>
 `/goalgames?`<br>

# Rosters

`GET https://api-web.nhle.com/v1/roster/TEAM_ABBR/SEASON_ID` | 

e.g. `https://api-web.nhle.com/v1/roster/buf/20232024`

`GET https://api-web.nhle.com/v1/roster-season/TEAM_ABBR` | ADD description

# Game details

`GET https://api-web.nhle.com/v1/score/now` | Linescore details

`GET https://api-web.nhle.com/v1/gamecenter/GAME_ID/boxscore` |  Boxscore details
`GET https://api-web.nhle.com/v1/gamecenter/GAME_ID/play-by-play` | PBP details

These two combined make what the previous live JSON used to be. Details like the time
of the day when the game ends are gone completely.

# Player search

`GET https://search.d3.nhle.com/api/v1/search/player?culture=en-us&limit=20&q=STRING` | Searches for a string. Culture is the locale, and active=0|1 may be specified.
