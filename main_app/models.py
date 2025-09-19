from django.db import models

#  Choices Enums
ROLES = (
    ('TEACHER','Teacher'),
    ('STUDENT','Student'),
    ('PARENT','Parent'),
    ('PARTNER','Partner'),
    ('ADMIN','Admin'),
)

# To-Do List for Classes

## Orgs
# - [ ] Organization  
#   -> has many OrgMembership  
#   -> has many Course  

# - [ ] OrgMembership  
#   -> belongs to Organization  
#   -> belongs to User  

## Courses & Enrollment
# - [ ] Course  
#   -> belongs to Organization  
#   -> belongs to User (teacher)  
#   -> has many CourseMember  
#   -> has many Assignment  
#   -> has many LiveSession  

# - [ ] CourseMember  
#   -> belongs to Course  
#   -> belongs to User  

## Quizzes & Content
# - [ ] Quiz  
#   -> belongs to User (owner)  
#   -> has many QuizVersion  
#   -> has many QuizTag  
#   -> has many Assignment  
#   -> has many Listing  

# - [ ] QuizVersion  
#   -> belongs to Quiz  
#   -> has many Question  
#   -> has many LiveSession  

# - [ ] Question  
#   -> belongs to QuizVersion  
#   -> has many Choice  
#   -> has many QuestionMedia  
#   -> has many AttemptItem  

# - [ ] Choice  
#   -> belongs to Question  
#   -> has many ChoiceMedia  

# - [ ] QuestionMedia  
#   -> belongs to Question  

# - [ ] ChoiceMedia  
#   -> belongs to Choice  

# - [ ] Tag  
#   -> has many QuizTag  

# - [ ] QuizTag  
#   -> belongs to Quiz  
#   -> belongs to Tag  

## Assignments & Attempts
# - [ ] Assignment  
#   -> belongs to Course  
#   -> belongs to Quiz  
#   -> has many Attempt  

# - [ ] Attempt  
#   -> belongs to Assignment  
#   -> belongs to User  
#   -> has one AttemptScore  
#   -> has many AttemptItem  

# - [ ] AttemptItem  
#   -> belongs to Attempt  
#   -> belongs to Question  

# - [ ] AttemptScore  
#   -> belongs to Attempt (OneToOne)  

## Live Sessions
# - [ ] LiveSession  
#   -> belongs to QuizVersion  
#   -> belongs to Course  
#   -> belongs to User (host)  
#   -> has many LiveParticipant  
#   -> has many LiveEvent  
#   -> has many LiveLeaderboard  

# - [ ] LiveParticipant  
#   -> belongs to LiveSession  
#   -> belongs to User  
#   -> has many LiveLeaderboard  

# - [ ] LiveEvent  
#   -> belongs to LiveSession  

# - [ ] LiveLeaderboard  
#   -> belongs to LiveSession  
#   -> belongs to LiveParticipant  

## Gamification
# - [ ] XPTransaction  
#   -> belongs to User  

# - [ ] Badge  
#   -> has many UserBadge  

# - [ ] UserBadge  
#   -> belongs to User  
#   -> belongs to Badge  

## Marketplace & Wallets
# - [ ] Wallet  
#   -> belongs to User (OneToOne)  
#   -> has many Payout  

# - [ ] Listing  
#   -> belongs to Quiz  
#   -> belongs to User (seller)  
#   -> has many Purchase  

# - [ ] Purchase  
#   -> belongs to Listing  
#   -> belongs to User (buyer)  

# - [ ] Payout  
#   -> belongs to Wallet  


# Dependency Tree Map

# User
# ├── OrgMembership
# │   └── Organization
# │
# ├── Course
# │   ├── CourseMember
# │   ├── Assignment
# │   │   └── Attempt
# │   │       ├── AttemptScore
# │   │       └── AttemptItem
# │   │           └── Question
# │   │               └── QuizVersion
# │   │                   └── Quiz
# │   └── LiveSession
# │       ├── LiveParticipant
# │       │   └── LiveLeaderboard
# │       ├── LiveEvent
# │       └── LiveLeaderboard
# │
# ├── Quiz
# │   ├── QuizVersion
# │   │   └── Question
# │   │       ├── Choice
# │   │       │   └── ChoiceMedia
# │   │       ├── QuestionMedia
# │   │       └── AttemptItem (via Attempt)
# │   ├── QuizTag
# │   │   └── Tag
# │   └── Listing
# │       ├── Purchase
# │       └── Payout (via Wallet)
# │
# ├── Wallet
# │   └── Payout
# │
# ├── XPTransaction
# ├── Badge
# │   └── UserBadge
# │
# └── Organization
#     ├── OrgMembership
#     └── Course
