# Field Recommendations for Account Models

## 🚨 Critical Missing Fields

### 1. **CustomerProfile Model** - COMPLETELY MISSING!
Your system has a CUSTOMER role but no profile model. This is essential for:
- Storing customer contact details
- Travel preferences
- Booking history tracking
- Emergency contacts

### 2. **Status Fields** (SupplierProfile & ResellerProfile)
Currently no way to track if accounts are:
- Pending verification
- Active
- Suspended/banned

### 3. **Email Verification** (CustomUser)
No email verification system - security risk!

### 4. **Banking/Payout Information** (ResellerProfile)
No way to pay commissions to resellers!

---

## 📋 Recommended Field Additions

### CustomUser Model
```python
email_verified = models.BooleanField(default=False)
email_verified_at = models.DateTimeField(null=True, blank=True)
phone_number = models.CharField(max_length=20, blank=True)
avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
timezone = models.CharField(max_length=50, default='UTC')
language = models.CharField(max_length=10, default='en')
```

### SupplierProfile Model
```python
status = models.CharField(...)  # PENDING/ACTIVE/SUSPENDED
website = models.URLField(blank=True)
country = models.CharField(max_length=100, blank=True)
logo = models.ImageField(...)
description = models.TextField(blank=True)
commission_rate = models.DecimalField(...)  # What they pay marketplace
bank_account_name = models.CharField(...)  # For supplier payouts
contact_email = models.EmailField(blank=True)
```

### ResellerProfile Model
```python
status = models.CharField(...)  # PENDING/ACTIVE/SUSPENDED
bio = models.TextField(blank=True)
bank_account_name = models.CharField(...)  # CRITICAL for commission payouts!
bank_account_number = models.CharField(...)
bank_name = models.CharField(...)
minimum_payout_threshold = models.DecimalField(...)
total_bookings = models.PositiveIntegerField(default=0)
total_commission_earned = models.DecimalField(...)
is_verified = models.BooleanField(default=False)
```

### StaffProfile Model
```python
employee_id = models.CharField(...)
hire_date = models.DateField(...)
manager = models.ForeignKey('self', ...)  # Org hierarchy
work_email = models.EmailField(blank=True)
```

### CustomerProfile Model (NEW - REQUIRED!)
```python
first_name, last_name
phone_number, address, city, country
date_of_birth, gender
travel_interests (JSON)
emergency_contact_name, emergency_contact_phone
```

---

## 🔥 Priority Ranking

### Must Have (Implement First):
1. ✅ CustomerProfile model
2. ✅ Email verification on CustomUser
3. ✅ Status fields on SupplierProfile & ResellerProfile
4. ✅ Banking info on ResellerProfile (for payouts)
5. ✅ Phone number on CustomUser

### Should Have (Next Phase):
6. SupplierProfile: logo, description, commission_rate
7. ResellerProfile: bio, statistics (total_bookings, etc.)
8. StaffProfile: employee_id, manager relationship
9. CustomUser: avatar, timezone, language

### Nice to Have (Future):
10. Two-factor authentication
11. Notification preferences
12. Social media links
13. Rating/review aggregations

---

## 💡 Implementation Notes

- **Status fields**: Use TextChoices enum like UserRole
- **Banking info**: Consider encryption for sensitive data
- **Statistics fields**: Can be computed or cached via signals
- **Images**: Don't forget to add Pillow to requirements.txt
- **JSON fields**: For flexible data like social_media_links

