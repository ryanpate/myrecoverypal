# apps/accounts/migrations/0002_add_community_features.py
# Generated migration for community features

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserConnection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('connection_type', models.CharField(choices=[('follow', 'Following'), ('block', 'Blocked'), ('friend', 'Friend')], default='follow', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_mutual', models.BooleanField(default=False)),
                ('follower', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='following_connections', to=settings.AUTH_USER_MODEL)),
                ('following', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='follower_connections', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['follower', 'connection_type'], name='accounts_us_followe_b4c8b5_idx'),
                    models.Index(fields=['following', 'connection_type'], name='accounts_us_followi_7c8f9e_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='SponsorRelationship',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending Approval'), ('active', 'Active'), ('completed', 'Completed'), ('declined', 'Declined'), ('terminated', 'Terminated')], default='pending', max_length=20)),
                ('started_date', models.DateField(blank=True, null=True)),
                ('ended_date', models.DateField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, help_text='Private notes about the relationship')),
                ('meeting_frequency', models.CharField(blank=True, help_text='e.g., Weekly, Bi-weekly, As needed', max_length=50)),
                ('communication_method', models.CharField(blank=True, help_text='e.g., Phone calls, In-person, Video chat', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('sponsor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sponsee_relationships', to=settings.AUTH_USER_MODEL)),
                ('sponsee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sponsor_relationships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['sponsor', 'status'], name='accounts_sp_sponsor_bb79f8_idx'),
                    models.Index(fields=['sponsee', 'status'], name='accounts_sp_sponsee_a8f2e9_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='RecoveryBuddy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('active', 'Active'), ('paused', 'Paused'), ('ended', 'Ended')], default='pending', max_length=20)),
                ('started_date', models.DateField(blank=True, null=True)),
                ('ended_date', models.DateField(blank=True, null=True)),
                ('check_in_frequency', models.CharField(blank=True, help_text='How often you want to check in with each other', max_length=50)),
                ('shared_goals', models.TextField(blank=True, help_text='Shared recovery goals and commitments')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buddy_relationships_as_user1', to=settings.AUTH_USER_MODEL)),
                ('user2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buddy_relationships_as_user2', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['user1', 'status'], name='accounts_re_user1_i_e6f8b9_idx'),
                    models.Index(fields=['user2', 'status'], name='accounts_re_user2_s_f9e8c7_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='RecoveryGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('group_type', models.CharField(choices=[('addiction_type', 'By Addiction Type'), ('location', 'Location-based'), ('recovery_stage', 'Recovery Stage'), ('interest', 'Shared Interest'), ('age_group', 'Age Group'), ('gender', 'Gender-specific'), ('family', 'Family/Supporters'), ('professional', 'Professional Support')], max_length=20)),
                ('privacy_level', models.CharField(choices=[('public', 'Public - Anyone can join'), ('private', 'Private - Approval required'), ('secret', 'Secret - Invitation only')], default='public', max_length=10)),
                ('max_members', models.PositiveIntegerField(blank=True, null=True)),
                ('location', models.CharField(blank=True, max_length=100)),
                ('meeting_schedule', models.CharField(blank=True, max_length=200)),
                ('group_image', models.ImageField(blank=True, upload_to='groups/')),
                ('group_color', models.CharField(default='#52b788', max_length=7)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('creator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_groups', to=settings.AUTH_USER_MODEL)),
                ('moderators', models.ManyToManyField(blank=True, related_name='moderated_groups', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
                'indexes': [
                    models.Index(fields=['group_type', 'privacy_level'], name='accounts_re_group_t_a8f7e6_idx'),
                    models.Index(fields=['is_active', 'created_at'], name='accounts_re_is_acti_f7e6d5_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='GroupMembership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending Approval'), ('active', 'Active Member'), ('moderator', 'Moderator'), ('admin', 'Administrator'), ('banned', 'Banned'), ('left', 'Left Group')], default='pending', max_length=20)),
                ('joined_date', models.DateField(blank=True, null=True)),
                ('left_date', models.DateField(blank=True, null=True)),
                ('role_notes', models.TextField(blank=True)),
                ('last_active', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='accounts.recoverygroup')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [
                    models.Index(fields=['user', 'status'], name='accounts_gr_user_id_f8e7d6_idx'),
                    models.Index(fields=['group', 'status'], name='accounts_gr_group_i_e7d6c5_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='GroupPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('post_type', models.CharField(choices=[('discussion', 'Discussion'), ('milestone', 'Milestone Share'), ('resource', 'Resource Share'), ('question', 'Question'), ('support', 'Support Request'), ('event', 'Event/Meeting')], default='discussion', max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('is_pinned', models.BooleanField(default=False)),
                ('is_anonymous', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_posts', to=settings.AUTH_USER_MODEL)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='posts', to='accounts.recoverygroup')),
                ('likes', models.ManyToManyField(blank=True, related_name='liked_group_posts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-is_pinned', '-created_at'],
                'indexes': [
                    models.Index(fields=['group', 'post_type'], name='accounts_gr_group_i_f8e9a7_idx'),
                    models.Index(fields=['author', 'created_at'], name='accounts_gr_author__e9a7b8_idx'),
                ],
            },
        ),
        # Add unique constraints
        migrations.AddConstraint(
            model_name='userconnection',
            constraint=models.UniqueConstraint(fields=('follower', 'following', 'connection_type'), name='unique_user_connection'),
        ),
        migrations.AddConstraint(
            model_name='sponsorrelationship',
            constraint=models.UniqueConstraint(fields=('sponsor', 'sponsee'), name='unique_sponsor_relationship'),
        ),
        migrations.AddConstraint(
            model_name='recoverybuddy',
            constraint=models.UniqueConstraint(fields=('user1', 'user2'), name='unique_recovery_buddy'),
        ),
        migrations.AddConstraint(
            model_name='groupmembership',
            constraint=models.UniqueConstraint(fields=('user', 'group'), name='unique_group_membership'),
        ),
    ]