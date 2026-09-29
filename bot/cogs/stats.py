import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from bot.database.db import db
from bot.utils.embeds import EmbedBuilder

class StatsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ticket_stats", description="View ticket system statistics / إحصائيات وتقارير التذاكر المتقدمة")
    async def ticket_stats(self, interaction: discord.Interaction):
        stats = db.get_statistics()
        
        embed = EmbedBuilder.create_embed(
            title="📊 تقرير وأداء نظام التذاكر (Ticket System Analytics)",
            description="نظرة شاملة ودقيقة على حركة التذاكر، سرعة الاستجابة، وتقييم أداء الطاقم الإداري.",
            color=EmbedBuilder.COLOR_PRIMARY
        )
        embed.add_field(name="🎫 إجمالي التذاكر", value=f"**{stats['total_tickets']}** تذكرة", inline=True)
        embed.add_field(name="🟢 تذاكر مفتوحة حالياً", value=f"**{stats['open_tickets']}**", inline=True)
        embed.add_field(name="🔴 تذاكر مغلقة ومنجزة", value=f"**{stats['closed_tickets']}**", inline=True)
        
        # Performance metrics
        avg_resp = stats.get("avg_response_minutes", 0.0)
        avg_resp_str = f"**{avg_resp}** دقيقة" if avg_resp > 0 else "غير محدد بعد"
        embed.add_field(name="⚡ متوسط سرعة أول رد", value=avg_resp_str, inline=True)

        avg_res = stats.get("avg_resolution_hours", 0.0)
        avg_res_str = f"**{avg_res}** ساعة" if avg_res > 0 else "غير محدد بعد"
        embed.add_field(name="⏳ متوسط مدة إنهاء التذكرة", value=avg_res_str, inline=True)

        embed.add_field(name="⭐ متوسط تقييم العملاء", value=f"**{stats['average_rating']} / 5.0**", inline=True)

        # Priority breakdown
        p_breakdown = stats.get("priority_breakdown", {})
        if p_breakdown:
            p_lines = [f"• **{k}:** `{v}` تذكرة" for k, v in p_breakdown.items() if k]
            if p_lines:
                embed.add_field(name="⚡ تصنيف الأولويات:", value="\n".join(p_lines[:5]), inline=False)

        top_staff_str = ""
        for s in stats["top_staff"]:
            user_mention = f"<@{s['staff_id']}>"
            top_staff_str += f"• {user_mention}: {round(s['avg_stars'], 2)} ⭐ ({s['total_ratings']} تقييم)\n"

        if top_staff_str:
            embed.add_field(name="🏆 أفضل موظفي الدعم الفني:", value=top_staff_str, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="view_ratings", description="View staff ratings / عرض تقييمات الموظفين")
    @app_commands.describe(staff="The staff member to view ratings for")
    async def view_ratings(self, interaction: discord.Interaction, staff: discord.Member = None):
        if staff:
            ratings = db.get_staff_ratings(staff.id)
            title = f"⭐ تقييمات {staff.display_name}"
        else:
            ratings = db.get_all_ratings(limit=10)
            title = "⭐ أحدث التقييمات العامة"

        if not ratings:
            return await interaction.response.send_message("❌ لا توجد تقييمات مسجلة حالياً.", ephemeral=True)

        embed = EmbedBuilder.create_embed(title=title, description="قائمة بأحدث تقييمات طاقم الدعم الفني:", color=EmbedBuilder.COLOR_WARNING)
        for r in ratings[:10]:
            staff_mention = f"<@{r['staff_id']}>"
            user_mention = f"<@{r['user_id']}>"
            feedback = r['feedback'] or "بدون تعليق"
            rating_id = r.get("id")
            embed.add_field(
                name=f"Rating #{rating_id} by {user_mention}",
                value=f"• **Staff:** {staff_mention}\n• **Stars:** {'⭐' * r['stars']}\n• **Feedback:** {feedback}\n• **Date:** {str(r['created_at'])[:10]}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="delete_rating", description="Delete a specific rating by ID / حذف تقييم محدد برقم التقييم")
    @app_commands.describe(rating_id="رقم التقييم المراد حذفه")
    async def delete_rating(self, interaction: discord.Interaction, rating_id: int):
        from bot.utils.permissions import PermissionHandler
        if not PermissionHandler.is_staff(interaction.user):
            return await interaction.response.send_message("❌ ليس لديك صلاحية لحذف التقييمات.", ephemeral=True)
            
        db.delete_rating(rating_id)
        await interaction.response.send_message(f"✅ تم حذف التقييم رقم #{rating_id} بنجاح.", ephemeral=True)

    @app_commands.command(name="delete_user_rating", description="Delete rating from a specific user for a specific staff / حذف تقييم عضو لإداري معين")
    @app_commands.describe(member="العضو صاحب التقييم", staff="الموظف/الإداري المقيّم")
    async def delete_user_rating(self, interaction: discord.Interaction, member: discord.Member, staff: discord.Member):
        from bot.utils.permissions import PermissionHandler
        if not PermissionHandler.is_staff(interaction.user):
            return await interaction.response.send_message("❌ ليس لديك صلاحية لحذف التقييمات.", ephemeral=True)

        guild_id = interaction.guild_id or 0
        deleted_count = db.delete_rating_by_user_and_staff(member.id, staff.id, guild_id)
        if deleted_count > 0:
            await interaction.response.send_message(f"✅ تم حذف {deleted_count} تقييم مقدم من {member.mention} للإداري {staff.mention} بنجاح.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ لم يتم العثور على أي تقييم مقدم من {member.mention} للإداري {staff.mention}.", ephemeral=True)

    @app_commands.command(name="clear_ratings", description="Clear staff ratings / مسح تقييمات موظف")
    @app_commands.describe(staff="The staff member to clear ratings for (leave empty for all)")
    async def clear_ratings(self, interaction: discord.Interaction, staff: discord.Member = None):
        from bot.utils.permissions import PermissionHandler
        rank = PermissionHandler.get_member_rank(interaction.user)
        if rank < PermissionHandler.ROLE_HIERARCHY["admin"]:
            return await interaction.response.send_message("❌ يتطلب هذا الأمر صلاحية (Admin) أو أعلى.", ephemeral=True)

        if staff:
            db.delete_staff_ratings(staff.id)
            await interaction.response.send_message(f"✅ تم مسح جميع تقييمات {staff.mention} بنجاح.")
        else:
            db.delete_all_ratings()
            await interaction.response.send_message("✅ تم مسح جميع التقييمات في النظام بنجاح.")

    def _build_leaderboard_embed(self, guild: discord.Guild) -> Optional[discord.Embed]:
        leaders = db.get_staff_leaderboard(guild.id, limit=10)
        if not leaders:
            return None

        embed = discord.Embed(
            title="🏆 لوحة شرف وصدارة طاقم الدعم الفني (Staff Leaderboard)",
            description=f"أفضل موظفي الدعم الفني في سيرفر **{guild.name}** حسب سرعة الإنجاز، النقاط، وتقييم النجوم:\n",
            color=0xFEE75C
        )

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        lines = []
        for idx, row in enumerate(leaders):
            badge = medals[idx] if idx < len(medals) else f"`#{idx+1}`"
            u_mention = f"<@{row['user_id']}>"
            pts = row.get("points", 0)
            tkts = row.get("tickets_handled", 0)
            stars = row.get("avg_stars", 0.0)
            star_str = f"{stars} ⭐" if stars > 0 else "بدون تقييم"
            lines.append(f"{badge} {u_mention} — **{pts}** نقطة | `{tkts}` تذكرة منجزة | {star_str}")

        embed.add_field(name="قائمة المتصدرين:", value="\n\n".join(lines), inline=False)
        embed.set_footer(text="نظام تذاكر ديسكورد المتقدم • تحديث فوري للنقاط والتقييم")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        return embed

    @app_commands.command(name="leaderboard", description="عرض لوحة شرف وصدارة طاقم الدعم الفني والنقاط (Staff Leaderboard)")
    async def leaderboard(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ يرجى استخدام هذا الأمر داخل السيرفر.", ephemeral=True)

        embed = self._build_leaderboard_embed(interaction.guild)
        if not embed:
            return await interaction.response.send_message("📊 لا توجد إحصائيات أو نقاط مسجلة لطاقم الدعم في هذا السيرفر بعد.", ephemeral=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="top", description="عرض صدارة وتوب طاقم الدعم الفني والنقاط (Top Staff Leaderboard)")
    async def top_slash(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ يرجى استخدام هذا الأمر داخل السيرفر.", ephemeral=True)

        embed = self._build_leaderboard_embed(interaction.guild)
        if not embed:
            return await interaction.response.send_message("📊 لا توجد إحصائيات أو نقاط مسجلة لطاقم الدعم في هذا السيرفر بعد.", ephemeral=True)

        await interaction.response.send_message(embed=embed)

    def _build_staff_profile_embed(self, guild: discord.Guild, member: discord.Member) -> discord.Embed:
        from bot.utils.permissions import PermissionHandler
        profile = db.get_staff_full_profile(guild.id, member.id)
        rank_val = PermissionHandler.get_member_rank(member)

        # Rank badge
        rank_title = "عضو عادي"
        if rank_val >= PermissionHandler.ROLE_HIERARCHY["owner"]:
            rank_title = "👑 مالك / إدارة عليا"
        elif rank_val >= PermissionHandler.ROLE_HIERARCHY["support_manager"]:
            rank_title = "🛡️ مدير الدعم الفني"
        elif rank_val >= PermissionHandler.ROLE_HIERARCHY["admin"]:
            rank_title = "⚡ مسؤول إداري (Admin)"
        elif rank_val >= PermissionHandler.ROLE_HIERARCHY["senior_support"]:
            rank_title = "🎖️ خبير دعم فني (Senior Support)"
        elif rank_val >= PermissionHandler.ROLE_HIERARCHY["support"]:
            rank_title = "👔 موظف دعم فني (Support)"

        rank_pos = f"#{profile['rank']}" if profile.get("rank") else "غير مصنف"

        embed = discord.Embed(
            title=f"👔 ملف وإنجازات الموظف • {member.display_name}",
            description=(
                f"👤 **الموظف:** {member.mention} (`{member.id}`)\n"
                f"🏷️ **الرتبة في النظام:** `{rank_title}`\n"
                f"🏆 **الترتيب في السيرفر:** `{rank_pos}` بين طاقم الدعم\n"
                f"───────────────────────────"
            ),
            color=0x5865F2
        )

        # 1. Ticket Performance & Points
        embed.add_field(
            name="📊 أداء التذاكر والنقاط:",
            value=(
                f"• **مجموع النقاط:** **`{profile['points']}`** نقطة\n"
                f"• **إجمالي التذاكر المستلمة:** `{profile['tickets_handled']}` تذكرة\n"
                f"• **التذاكر النشطة حالياً:** `{profile['tickets_active']}` تذكرة\n"
                f"• **التذاكر المنجزة والمغلقة:** `{profile['tickets_closed']}` تذكرة"
            ),
            inline=True
        )

        # 2. Ratings & Client Satisfaction
        stars_dist = profile.get("stars_distribution", {})
        stars_breakdown = f"5⭐ `{stars_dist.get(5, 0)}` | 4⭐ `{stars_dist.get(4, 0)}` | 3⭐ `{stars_dist.get(3, 0)}` | 2⭐ `{stars_dist.get(2, 0)}` | 1⭐ `{stars_dist.get(1, 0)}`"
        avg_stars_display = f"**{profile['avg_stars']} / 5.0 ⭐**" if profile['total_ratings'] > 0 else "*بدون تقييم بعد*"

        embed.add_field(
            name="⭐ تقييم رضا العملاء:",
            value=(
                f"• **المتوسط العام:** {avg_stars_display}\n"
                f"• **عدد التقييمات:** `{profile['total_ratings']}` تقييم\n"
                f"• **توزيع النجوم:**\n{stars_breakdown}"
            ),
            inline=True
        )

        # 3. Actions and Operations Breakdown
        actions_map = profile.get("actions_breakdown", {})
        action_names_ar = {
            "استلام التذكرة": "📌 استلام تذاكر",
            "إغلاق التذكرة": "🔒 إغلاق تذاكر",
            "إلغاء الاستلام": "🔓 إلغاء استلام",
            "تحويل التذكرة": "🔄 تحويل لموظف آخر",
            "تغيير القسم": "🏢 نقل وتغيير قسم",
            "تعديل الأولوية": "⚡ تعديل أولوية",
            "قفل التذكرة": "🔐 قفل التذكرة",
            "فك قفل التذكرة": "🔓 فك قفل التذكرة",
            "تعليق التذكرة": "⏸️ تعليق التذكرة",
            "استئناف التذكرة": "▶️ استئناف التذكرة",
            "إضافة ملاحظة إدارية": "📝 تدوين ملاحظات",
            "إعادة فتح التذكرة": "🔓 إعادة فتح",
            "حذف التذكرة": "🗑️ حذف تذاكر",
            "نداء صاحب التذكرة": "🔔 نداء العضو",
            "تغيير اسم التذكرة": "✏️ إعادة تسمية"
        }

        action_lines = []
        for act_raw, count in actions_map.items():
            label = action_names_ar.get(act_raw, f"• {act_raw}")
            action_lines.append(f"• **{label}:** `{count}` مرة")

        actions_text = "\n".join(action_lines[:8]) if action_lines else "*لا توجد عمليات مسجلة في السجل بعد*"
        embed.add_field(
            name=f"⚙️ سجل الإجراءات والعمليات المنفذة (`{profile['total_actions']}` عملية إجمالاً):",
            value=actions_text,
            inline=False
        )

        # 4. Latest feedbacks if any
        feedbacks = profile.get("feedbacks", [])
        if feedbacks:
            fb_lines = []
            for fb in feedbacks[:3]:
                u_str = f"<@{fb['user_id']}>" if fb.get('user_id') else "عميل"
                fb_lines.append(f"💬 \"{fb['feedback']}\" — {fb['stars']}⭐ ({u_str})")
            embed.add_field(
                name="💬 آخر آراء وتعليقات العملاء:",
                value="\n".join(fb_lines),
                inline=False
            )

        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)

        embed.set_footer(text=f"طلب بواسطة {guild.name} • ملف طاقم الدعم الفني المتقدم")
        embed.timestamp = discord.utils.utcnow()
        return embed

    @app_commands.command(name="staff_info", description="عرض ملف وإحصائيات وإنجازات موظف الدعم الفني بالكامل (Staff Profile & Actions)")
    @app_commands.describe(staff="الموظف المراد عرض ملفه (اتركه فارغاً لعرض ملفك)")
    async def staff_info_slash(self, interaction: discord.Interaction, staff: Optional[discord.Member] = None):
        if not interaction.guild:
            return await interaction.response.send_message("❌ يرجى استخدام هذا الأمر داخل السيرفر.", ephemeral=True)

        target = staff or interaction.user
        if not isinstance(target, discord.Member):
            target = interaction.guild.get_member(target.id) or target

        embed = self._build_staff_profile_embed(interaction.guild, target)
        await interaction.response.send_message(embed=embed)

    @commands.command(name="staff_info", aliases=["staff", "اداري", "مشرف", "طاقم", "بروفايل_اداري", "انجازات"])
    async def staff_info_prefix(self, ctx: commands.Context, staff: Optional[discord.Member] = None):
        if not ctx.guild:
            return await ctx.send("❌ يرجى استخدام هذا الأمر داخل السيرفر.")

        target = staff or ctx.author
        if not isinstance(target, discord.Member):
            target = ctx.guild.get_member(target.id) or target

        embed = self._build_staff_profile_embed(ctx.guild, target)
        await ctx.send(embed=embed)

    @commands.command(name="top", aliases=["leaderboard", "توب", "المتصدرين", "شرف"])
    async def top_prefix(self, ctx: commands.Context):
        if not ctx.guild:
            return await ctx.send("❌ يرجى استخدام هذا الأمر داخل السيرفر.")

        embed = self._build_leaderboard_embed(ctx.guild)
        if not embed:
            return await ctx.send("📊 لا توجد إحصائيات أو نقاط مسجلة لطاقم الدعم في هذا السيرفر بعد.")

        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCog(bot))
