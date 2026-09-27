import discord
from discord.ext import commands, tasks
from discord import app_commands
from typing import Optional
from datetime import datetime
import asyncio
import logging
from bot.database.db import db
from bot.views.panel_view import PanelView
from bot.utils.embeds import EmbedBuilder
from bot.utils.permissions import PermissionHandler

logger = logging.getLogger("discord_bot")

class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.inactivity_check.start()

    def cog_unload(self):
        self.inactivity_check.cancel()

    @tasks.loop(minutes=15)
    async def inactivity_check(self):
        """Background job to check inactive open tickets and warn or auto-close them."""
        try:
            for guild in self.bot.guilds:
                auto_close_hours = db.get_guild_setting(guild.id, "auto_close_hours", 0)
                if not auto_close_hours or auto_close_hours <= 0:
                    continue

                tickets = db.get_open_tickets_for_inactivity(guild.id)
                for t in tickets:
                    channel = guild.get_channel(t["channel_id"])
                    if not channel:
                        continue

                    # Reference time: last message from staff or ticket creation
                    created_str = t.get("created_at")
                    last_staff_str = t.get("last_staff_message_at")
                    ref_time_str = last_staff_str or created_str
                    if not ref_time_str:
                        continue

                    try:
                        ref_time = datetime.fromisoformat(ref_time_str)
                    except Exception:
                        continue

                    now = datetime.utcnow()
                    hours_inactive = (now - ref_time).total_seconds() / 3600.0

                    warn_threshold = max(1.0, auto_close_hours * 0.75)
                    is_warned = t.get("inactivity_warned", 0)

                    if hours_inactive >= auto_close_hours:
                        try:
                            embed = discord.Embed(
                                title="🔒 تم إغلاق التذكرة تلقائياً بسبب الخمول",
                                description=(
                                    f"نظراً لعدم وجود أي نشاط أو ردود في هذه التذكرة لأكثر من `{auto_close_hours}` ساعة، "
                                    f"تم إغلاق التذكرة تلقائياً من قبل النظام."
                                ),
                                color=EmbedBuilder.COLOR_DANGER
                            )
                            embed.set_footer(text="نظام الإغلاق التلقائي للخمول • Discord Ticket System")
                            await channel.send(embed=embed)

                            # Close in database
                            db.close_ticket(channel.id, 0)
                            db.mark_ticket_inactivity_warned(channel.id, 2)

                            # Log closure
                            log_ch_id = db.get_guild_setting(guild.id, "log_channel_id")
                            if log_ch_id:
                                log_ch = guild.get_channel(log_ch_id)
                                if log_ch:
                                    c_log = discord.Embed(
                                        title=f"🔒 [إغلاق خمول] تم إغلاق التذكرة #{t['id']}",
                                        description=f"تم إغلاق تذكرة العضو <@{t['user_id']}> تلقائياً بعد خمول استمر لمدة `{auto_close_hours}` ساعة.",
                                        color=EmbedBuilder.COLOR_DANGER
                                    )
                                    c_log.timestamp = discord.utils.utcnow()
                                    await log_ch.send(embed=c_log)

                            await asyncio.sleep(5)
                            await channel.delete(reason=f"Auto closed due to {auto_close_hours}h inactivity")
                        except Exception as e:
                            logger.error(f"Error auto-closing inactive ticket {t.get('id')}: {e}")

                    elif hours_inactive >= warn_threshold and not is_warned:
                        try:
                            rem_hours = round(max(0.5, auto_close_hours - hours_inactive), 1)
                            w_embed = discord.Embed(
                                title="⚠️ تنبيه خمول التذكرة (Inactivity Warning)",
                                description=(
                                    f"مرحباً <@{t['user_id']}> 👋،\n\n"
                                    f"لم يتم تسجيل أي رد أو تفاعل في هذه التذكرة منذ فترة.\n"
                                    f"يرجى الرد إذا كنت بحاجة للمساعدة، وإلا سيتم إغلاق التذكرة تلقائياً خلال **{rem_hours} ساعة**."
                                ),
                                color=EmbedBuilder.COLOR_WARNING
                            )
                            w_embed.set_footer(text="نظام الحماية من تراكم التذاكر الخاملة")
                            await channel.send(content=f"<@{t['user_id']}>", embed=w_embed)
                            db.mark_ticket_inactivity_warned(channel.id, 1)
                        except Exception as e:
                            pass
        except Exception as loop_err:
            logger.error(f"Inactivity loop error: {loop_err}")

    @inactivity_check.before_loop
    async def before_inactivity(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="setup_panel", description="إنشاء لوحة تذاكر بايمبد مخصص وصورة السيرفر / Post custom ticket panel embed")
    @app_commands.describe(
        title="عنوان اللوحة (مثال: مركز الدعم الفني والتذاكر)",
        description="وصف اللوحة والتعليمات الخاصة بالعملاء",
        color_hex="رمز اللون بالتنسيق السداسي عشر (مثال: 5865F2 أو 10b981)",
        image_url="رابط صورة الهيدر أو البانل الكبير (اختياري)",
        footer_text="نص الهامش السفلي المخصص (اختياري)",
        category1_name="اسم القسم 1 (مثال: الدعم الفني)",
        category1_emoji="إيموجي القسم 1 (مثال: 💬)",
        category1_desc="وصف قصير للقسم 1",
        category2_name="اسم القسم 2 (مثال: الشكاوى والمبيعات)",
        category2_emoji="إيموجي القسم 2 (مثال: 💳)",
        category2_desc="وصف قصير للقسم 2",
        category3_name="اسم القسم 3 (اختياري)",
        category3_emoji="إيموجي القسم 3",
        category3_desc="وصف قصير للقسم 3",
        category4_name="اسم القسم 4 (اختياري)",
        category4_emoji="إيموجي القسم 4",
        category4_desc="وصف قصير للقسم 4",
        category5_name="اسم القسم 5 (اختياري)",
        category5_emoji="إيموجي القسم 5",
        category5_desc="وصف قصير للقسم 5"
    )
    async def setup_panel(
        self,
        interaction: discord.Interaction,
        title: str = "مركز الدعم الفني والتذاكر",
        description: str = "أهلاً بك! يرجى اختيار القسم المناسب من القائمة المنسدلة أسفله لفتح تذكرة مباشرة مع طاقم الدعم.",
        color_hex: str = "5865F2",
        image_url: Optional[str] = None,
        footer_text: Optional[str] = None,
        category1_name: str = "دعم عام / General Support",
        category1_emoji: str = "💬",
        category1_desc: str = "انقر لفتح تذكرة للمساعدة العامة والاستفسارات",
        category1_points: int = 5,
        category2_name: str = "المبيعات والاشتراكات / Billing & Sales",
        category2_emoji: str = "💳",
        category2_desc: str = "انقر لفتح تذكرة بخصوص المبيعات والدفع",
        category2_points: int = 10,
        category3_name: Optional[str] = None,
        category3_emoji: Optional[str] = "⚙️",
        category3_desc: Optional[str] = None,
        category3_points: int = 5,
        category4_name: Optional[str] = None,
        category4_emoji: Optional[str] = "🛠️",
        category4_desc: Optional[str] = None,
        category4_points: int = 5,
        category5_name: Optional[str] = None,
        category5_emoji: Optional[str] = "⭐",
        category5_desc: Optional[str] = None,
        category5_points: int = 5
    ):
        if not PermissionHandler.is_staff(interaction.user):
            return await interaction.response.send_message("❌ تحتاج إلى صلاحيات الإدارة لاستخدام هذا الأمر.", ephemeral=True)

        try:
            clean_color = color_hex.replace("#", "").strip()
            color_int = int(clean_color, 16)
        except ValueError:
            color_int = EmbedBuilder.COLOR_PRIMARY

        # Construct categories list
        categories = []
        raw_cats = [
            (category1_name, category1_emoji, category1_desc, "cat_1", category1_points),
            (category2_name, category2_emoji, category2_desc, "cat_2", category2_points),
            (category3_name, category3_emoji, category3_desc, "cat_3", category3_points),
            (category4_name, category4_emoji, category4_desc, "cat_4", category4_points),
            (category5_name, category5_emoji, category5_desc, "cat_5", category5_points),
        ]

        for name, emoji, desc, cat_id, points in raw_cats:
            if name and name.strip():
                categories.append({
                    "id": cat_id,
                    "name": name.strip(),
                    "emoji": emoji.strip() if emoji else "🎫",
                    "description": desc.strip() if desc else "انقر لفتح تذكرة جديدة",
                    "points": points
                })

        if not categories:
            categories = [
                {"id": "cat_1", "name": "دعم عام", "emoji": "💬", "description": "تذكرة دعم عام"},
                {"id": "cat_2", "name": "المبيعات", "emoji": "💳", "description": "تذكرة مبيعات"}
            ]

        # 1. Save Panel to SQLite Database
        panel_id = db.save_panel(
            title=title,
            description=description,
            color=color_int,
            categories=categories,
            channel_id=interaction.channel_id,
            image_url=image_url,
            footer_text=footer_text
        )

        # 2. Construct Embed featuring Server Icon (صورة السيرفر) as thumbnail & footer icon
        embed = EmbedBuilder.panel_embed(
            title=title,
            description=description,
            color=color_int,
            guild=interaction.guild,
            image_url=image_url,
            footer_text=footer_text,
            categories=categories
        )

        # 3. Attach Panel View with Interactive Dropdown Select Menu
        view = PanelView(categories=categories, panel_id=panel_id)
        msg = await interaction.channel.send(embed=embed, view=view)

        # Update database with message_id
        db.update_panel_message_id(panel_id, msg.id)

        server_icon_status = "موجودة وتم تضمينها في الايمبد 🖼️" if (interaction.guild and interaction.guild.icon) else "غير محددة في السيرفر"

        await interaction.response.send_message(
            f"✅ **تم إنشاء ونشر لوحة التذاكر المخصصة بنجاح!**\n"
            f"• **معرف اللوحة:** `{panel_id}`\n"
            f"• **عدد الأقسام:** `{len(categories)}` قسم\n"
            f"• **صورة السيرفر:** {server_icon_status}\n"
            f"• **القناة:** {interaction.channel.mention}",
            ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(TicketsCog(bot))
