from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q


# To-Do List for Classes

## Orgs
# - [X] Organization  
#   -> has many OrgMembership  
#   -> has many Course  

# - [X] OrgMembership  
#   -> belongs to Organization  
#   -> belongs to User  

## Courses & Enrollment
# - [X] Course  
#   -> belongs to Organization  
#   -> belongs to User (teacher)  
#   -> has many CourseMember  
#   -> has many Assignment  
#   -> has many LiveSession  

# - [X] CourseMember  
#   -> belongs to Course  
#   -> belongs to User  

## Quizzes & Content
# - [X] Quiz  
#   -> belongs to User (owner)  
#   -> has many QuizVersion  
#   -> has many QuizTag  
#   -> has many Assignment  
#   -> has many Listing  

# - [X] QuizVersion  
#   -> belongs to Quiz  
#   -> has many Question  
#   -> has many LiveSession  

# - [X] Question  
#   -> belongs to QuizVersion  
#   -> has many Choice  
#   -> has many QuestionMedia  
#   -> has many AttemptItem  

# - [X] Choice  
#   -> belongs to Question  
#   -> has many ChoiceMedia  

# - [X] QuestionMedia  
#   -> belongs to Question  

# - [X] ChoiceMedia  
#   -> belongs to Choice  

# - [X] Tag  
#   -> has many QuizTag  

# - [X] QuizTag  
#   -> belongs to Quiz  
#   -> belongs to Tag  

## Assignments & Attempts
# - [X] Assignment  
#   -> belongs to Course  
#   -> belongs to Quiz  
#   -> has many Attempt  

# - [X] Attempt  
#   -> belongs to Assignment  
#   -> belongs to User  
#   -> has one AttemptScore  
#   -> has many AttemptItem  

# - [X] AttemptItem  
#   -> belongs to Attempt  
#   -> belongs to Question  

# - [X] AttemptScore  
#   -> belongs to Attempt (OneToOne)  

## Live Sessions
# - [X] LiveSession  
#   -> belongs to QuizVersion  
#   -> belongs to Course  
#   -> belongs to User (host)  
#   -> has many LiveParticipant  
#   -> has many LiveEvent  
#   -> has many LiveLeaderboard  

# - [X] LiveParticipant  
#   -> belongs to LiveSession  
#   -> belongs to User  
#   -> has many LiveLeaderboard  

# - [X] LiveEvent  
#   -> belongs to LiveSession  

# - [X] LiveLeaderboard  
#   -> belongs to LiveSession  
#   -> belongs to LiveParticipant  

## Gamification
# - [X] XPTransaction  
#   -> belongs to User  

# - [X] Badge  
#   -> has many UserBadge  

# - [X] UserBadge  
#   -> belongs to User  
#   -> belongs to Badge  

## Marketplace & Wallets
# - [X] Wallet  
#   -> belongs to User (OneToOne)  
#   -> has many Payout  

# - [X] Listing  
#   -> belongs to Quiz  
#   -> belongs to User (seller)  
#   -> has many Purchase  

# - [X] Purchase  
#   -> belongs to Listing  
#   -> belongs to User (buyer)  

# - [X] Payout  
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
