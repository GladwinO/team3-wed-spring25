from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from messaging.models import Message
from listings.models import Listing
from booking.models import Booking
from django import forms


class MessagingViewsTest(TestCase):
    def setUp(self):
        """Create test users and messages"""
        self.user1 = User.objects.create_user(
            username="testuser1", email="user1@test.com", password="testpassword1"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", email="user2@test.com", password="testpassword2"
        )
        self.user3 = User.objects.create_user(
            username="testuser3", email="user3@test.com", password="testpassword3"
        )

        self.message1 = Message.objects.create(
            sender=self.user1,
            recipient=self.user2,
            subject="Test Subject 1",
            body="Test body 1",
        )

        self.message2 = Message.objects.create(
            sender=self.user2,
            recipient=self.user1,
            subject="Test Subject 2",
            body="Test body 2",
        )

        self.client = Client()

    def test_inbox_view_authenticated(self):
        """Test inbox access for authenticated users"""
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.get(reverse("inbox"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "messaging/inbox.html")
        self.assertIn("messages_inbox", response.context)
        self.assertEqual(len(response.context["messages_inbox"]), 1)
        self.assertEqual(response.context["messages_inbox"][0], self.message2)

    def test_inbox_view_unauthenticated(self):
        """Test inbox access for unauthenticated users"""
        response = self.client.get(reverse("inbox"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_sent_messages_view_authenticated(self):
        """Test sent messages access for authenticated users"""
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.get(reverse("sent_messages"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "messaging/sent_messages.html")
        self.assertIn("messages_sent", response.context)
        self.assertEqual(len(response.context["messages_sent"]), 1)
        self.assertEqual(response.context["messages_sent"][0], self.message1)

    def test_sent_messages_view_unauthenticated(self):
        """Test sent messages access for unauthenticated users"""
        response = self.client.get(reverse("sent_messages"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/"))

    def test_message_detail_as_recipient(self):
        """Test viewing message details as recipient"""
        self.client.login(username="testuser2", password="testpassword2")
        response = self.client.get(reverse("message_detail", args=[self.message1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "messaging/message_detail.html")

        # Verify message is marked as read
        self.message1.refresh_from_db()
        self.assertTrue(self.message1.read)

    def test_message_detail_as_sender(self):
        """Test viewing message details as sender"""
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.get(reverse("message_detail", args=[self.message1.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "messaging/message_detail.html")

    def test_message_detail_unauthorized(self):
        """Test unauthorized access to message details"""
        self.client.login(username="testuser3", password="testpassword3")
        response = self.client.get(reverse("message_detail", args=[self.message1.id]))

        self.assertEqual(response.status_code, 403)

    def test_delete_message_as_recipient(self):
        """Test deleting a message as recipient"""
        self.client.login(username="testuser2", password="testpassword2")
        response = self.client.post(reverse("delete_message", args=[self.message1.id]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("inbox"))
        self.assertFalse(Message.objects.filter(id=self.message1.id).exists())

    def test_delete_message_as_sender(self):
        """Test deleting a message as sender"""
        self.client.login(username="testuser1", password="testpassword1")
        response = self.client.post(reverse("delete_message", args=[self.message1.id]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("inbox"))
        self.assertFalse(Message.objects.filter(id=self.message1.id).exists())

    def test_delete_message_unauthorized(self):
        """Test unauthorized attempt to delete a message"""
        self.client.login(username="testuser3", password="testpassword3")
        response = self.client.post(reverse("delete_message", args=[self.message1.id]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Message.objects.filter(id=self.message1.id).exists())


class ComposeMessagingTests(TestCase):
    def setUp(self):
        """Create test users, listings and relationships"""
        # Create users
        self.owner = User.objects.create_user(
            username="spotowner", email="owner@test.com", password="ownerpass"
        )
        self.renter = User.objects.create_user(
            username="renter", email="renter@test.com", password="renterpass"
        )
        self.unrelated_user = User.objects.create_user(
            username="stranger", email="stranger@test.com", password="strangerpass"
        )
        self.admin_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            is_staff=True,
        )

        # Create a listing for the owner
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Test Parking Spot",
            location="123 Test St",
            rent_per_hour=10.0,
            description="Test description",
        )

    def test_no_listings_or_bookings(self):
        """Test when user has no listings or bookings they can't message anyone"""
        self.client.login(username="stranger", password="strangerpass")

        # Try to access compose page
        response = self.client.get(reverse("compose_message"))

        # Should redirect to inbox
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("inbox"))
        self.assertEqual(
            response.wsgi_request.session["error_message"],
            "You don't have any users to message yet. You need to either book "
            "a listing or have someone book your listing first.",
        )

    def test_has_listing_no_bookings(self):
        """Test when user has a listing but no bookings they can't message anyone"""
        self.client.login(username="spotowner", password="ownerpass")

        response = self.client.get(reverse("compose_message"))

        # Should redirect to inbox
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("inbox"))
        self.assertEqual(
            response.wsgi_request.session["error_message"],
            "You don't have any users to message yet. You need to either book "
            "a listing or have someone book your listing first.",
        )

    def test_renter_can_message_owner(self):
        """Test when user has made a booking they can message the owner"""
        # Create a booking
        Booking.objects.create(
            user=self.renter,
            listing=self.listing,
            email="renter@test.com",
            status="APPROVED",
        )

        self.client.login(username="renter", password="renterpass")
        response = self.client.get(reverse("compose_message"))

        # Should access page
        self.assertEqual(response.status_code, 200)

        # Owner should be in available recipients
        self.assertIn(
            self.owner.id,
            [user.id for user in response.context["available_recipients"]],
        )

        # Test sending a message
        data = {
            "recipient": self.owner.id,
            "subject": "Question about spot",
            "body": "Is parking available next week?",
        }
        response = self.client.post(reverse("compose_message"), data)

        # Should succeed
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Message.objects.filter(sender=self.renter, recipient=self.owner).exists()
        )
        self.assertEqual(
            response.wsgi_request.session["success_message"],
            "Message sent successfully!",
        )

    def test_owner_can_message_renter(self):
        """Test when someone has booked your listing you can message them"""
        # Create a booking
        Booking.objects.create(
            user=self.renter,
            listing=self.listing,
            email="renter@test.com",
            status="APPROVED",
        )

        self.client.login(username="spotowner", password="ownerpass")
        response = self.client.get(reverse("compose_message"))

        # Should access page
        self.assertEqual(response.status_code, 200)

        # Renter should be in available recipients
        self.assertIn(
            self.renter.id,
            [user.id for user in response.context["available_recipients"]],
        )

        # Test sending a message
        data = {
            "recipient": self.renter.id,
            "subject": "Booking Confirmation",
            "body": "Your booking is confirmed!",
        }

        response = self.client.post(reverse("compose_message"), data)

        # Should succeed
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Message.objects.filter(sender=self.owner, recipient=self.renter).exists()
        )
        self.assertEqual(
            response.wsgi_request.session["success_message"],
            "Message sent successfully!",
        )

    def test_messaging_unauthorized_user(self):
        """Test trying to message a user you're not connected with"""
        # Create a booking to enable messaging for renter
        Booking.objects.create(
            user=self.renter,
            listing=self.listing,
            email="renter@test.com",
            status="APPROVED",
        )

        self.client.login(username="renter", password="renterpass")

        # Try to compose to unrelated user
        response = self.client.get(
            reverse("compose_message_to", args=[self.unrelated_user.id])
        )

        # Should redirect with error
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("inbox"))
        self.assertEqual(
            response.wsgi_request.session["error_message"],
            "You cannot message this user as you haven't had any booking interactions.",
        )

    def test_messaging_admin_user(self):
        """Test users can message admin users regardless of relationship"""
        self.client.login(username="stranger", password="strangerpass")

        # Stranger with no relationships should still be able to message admin
        response = self.client.get(
            reverse("compose_message_to", args=[self.admin_user.id])
        )

        # Should allow access
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["recipient"], self.admin_user)

    def test_form_security(self):
        """Test form validation prevents messaging unauthorized users"""
        # Create a booking
        Booking.objects.create(
            user=self.renter,
            listing=self.listing,
            email="renter@test.com",
            status="APPROVED",
        )

        self.client.login(username="renter", password="renterpass")

        # Try to send message to unauthorized user via POST
        data = {
            "recipient": self.unrelated_user.id,
            "subject": "Unauthorized message",
            "body": "This should fail",
        }

        response = self.client.post(reverse("compose_message"), data)

        # Should stay on form with error
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Message.objects.filter(recipient=self.unrelated_user).exists())

    def test_admin_message_form(self):
        """Test that users can access the admin message form"""
        self.client.login(username="stranger", password="strangerpass")

        # Even users with no relationships should be able to access admin message form
        response = self.client.get(reverse("compose_admin_message"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_admin_message"])
        self.assertIsInstance(
            response.context["form"].fields["recipient"].widget, forms.HiddenInput
        )

    def test_send_admin_message(self):
        """Test sending a message to admin"""
        self.client.login(username="stranger", password="strangerpass")

        data = {
            "subject": "Help Request",
            "body": "I need assistance with my account",
        }

        response = self.client.post(reverse("compose_admin_message"), data)

        # Should redirect to inbox
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("inbox"))

        # Should create message to admin
        message = Message.objects.filter(
            sender=self.unrelated_user, recipient=self.admin_user
        ).first()
        self.assertIsNotNone(message)
        self.assertEqual(message.subject, "[USER SUPPORT MESSAGE] Help Request")
        self.assertEqual(message.body, "I need assistance with my account")

    def test_admin_can_message_anyone(self):
        """Test that admin users can message anyone"""
        self.client.login(username="admin", password="adminpass")

        # Admin should be able to access compose page
        response = self.client.get(reverse("compose_message"))

        self.assertEqual(response.status_code, 200)

        # All users should be in available recipients
        recipients_ids = [user.id for user in response.context["available_recipients"]]
        self.assertIn(self.owner.id, recipients_ids)
        self.assertIn(self.renter.id, recipients_ids)
        self.assertIn(self.unrelated_user.id, recipients_ids)

        # Admin should be able to message any user
        data = {
            "recipient": self.unrelated_user.id,
            "subject": "Admin message",
            "body": "This is an admin message",
        }

        response = self.client.post(reverse("compose_message"), data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Message.objects.filter(
                sender=self.admin_user, recipient=self.unrelated_user
            ).exists()
        )

    def test_reply_to_admin_message(self):
        """Test replying to an admin message"""
        # Create an admin message
        admin_message = Message.objects.create(
            sender=self.admin_user,
            recipient=self.unrelated_user,
            subject="Admin notification",
            body="Important information",
        )

        self.client.login(username="stranger", password="strangerpass")

        # View the message
        response = self.client.get(reverse("message_detail", args=[admin_message.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reply to Admin")

    def test_admin_sees_admin_label(self):
        """Test that admin username is labeled with [ADMIN]"""
        # Create an admin message
        admin_message = Message.objects.create(
            sender=self.admin_user,
            recipient=self.unrelated_user,
            subject="Admin notification",
            body="Important information",
        )

        self.client.login(username="stranger", password="strangerpass")

        # View the message
        response = self.client.get(reverse("message_detail", args=[admin_message.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "[ADMIN]")
