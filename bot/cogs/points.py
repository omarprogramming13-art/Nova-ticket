import discord
from discord.ext import commands
from discord import app_commands
from bot.database.db import db
from bot.utils.embeds import EmbedBuilder
from bot.utils.permissions import PermissionHandler
from typing import Optional

class PointsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="points_add", description="إضافة نقاط لعضو في طاقم الإدارة / Add points to a staff member")
    @app_commands.describe(member="العضو المراد إضافة النقاط له", points="عدد النقاط")
    async def points_add(self, interaction: discord.Interaction, member: discord.Member, points: int):
        if not PermissionHandler.is_admin(interaction.user):
            return await interaction.response.send_message("❌ هذا الأمر مخصص للإدارة العليا فقط.", ephemeral=True)
        
        db.update_staff_points(interaction.guild_id, member.id, points)
        await interaction.response.send_message(f"✅ تم إضافة **{points}** نقطة لـ {member.mention} بنجاح.")

    @app_commands.command(name="points_remove", description="خصم نقاط من عضو في طاقم الإدارة / Remove points from a staff member")
    @app_commands.describe(member="العضو المراد خصم النقاط منه", points="عدد النقاط")
    async def points_remove(self, interaction: discord.Interaction, member: discord.Member, points: int):
        if not PermissionHandler.is_admin(interaction.user):
            return await interaction.response.send_message("❌ هذا الأمر مخصص للإدارة العليا فقط.", ephemeral=True)
        
        db.update_staff_points(interaction.guild_id, member.id, -points)
        await interaction.response.send_message(f"✅ تم خصم **{points}** نقطة من {member.mention} بنجاح.")

    @app_commands.command(name="points_reset", description="تصفير نقاط عضو أو جميع طاقم الإدارة / Reset points for one or all staff")
    @app_commands.describe(member="العضو المراد تصفير نقاطه (اتركه فارغاً لتصفير نقاط الجميع)")
    async def points_reset(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        if not PermissionHandler.is_admin(interaction.user):
            return await interaction.response.send_message("❌ هذا الأمر مخصص للإدارة العليا فقط.", ephemeral=True)
        
        if member:
            db.reset_staff_points(interaction.guild_id, member.id)
            await interaction.response.send_message(f"✅ تم تصفير نقاط {member.mention} بنجاح.")
        else:
            db.reset_staff_points(interaction.guild_id)
            await interaction.response.send_message("✅ تم تصفير نقاط جميع أعضاء طاقم الإدارة بنجاح.")

    # Prefix Commands
    @commands.command(name="اضافة_نقاط", aliases=["اضافة", "add_points"])
    async def prefix_add_points(self, ctx: commands.Context, member: discord.Member, points: int):
        if not PermissionHandler.is_admin(ctx.author):
            return await ctx.send("❌ هذا الأمر مخصص للإدارة العليا فقط.")
        
        db.update_staff_points(ctx.guild.id, member.id, points)
        await ctx.send(f"✅ تم إضافة **{points}** نقطة لـ {member.mention} بنجاح.")

    @commands.command(name="خصم_نقاط", aliases=["خصم", "remove_points"])
    async def prefix_remove_points(self, ctx: commands.Context, member: discord.Member, points: int):
        if not PermissionHandler.is_admin(ctx.author):
            return await ctx.send("❌ هذا الأمر مخصص للإدارة العليا فقط.")
        
        db.update_staff_points(ctx.guild.id, member.id, -points)
        await ctx.send(f"✅ تم خصم **{points}** نقطة من {member.mention} بنجاح.")

    @commands.command(name="تصفير_نقاط", aliases=["تصفير", "reset_points"])
    async def prefix_reset_points(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        if not PermissionHandler.is_admin(ctx.author):
            return await ctx.send("❌ هذا الأمر مخصص للإدارة العليا فقط.")
        
        if member:
            db.reset_staff_points(ctx.guild.id, member.id)
            await ctx.send(f"✅ تم تصفير نقاط {member.mention} بنجاح.")
        else:
            db.reset_staff_points(ctx.guild.id)
            await ctx.send("✅ تم تصفير نقاط جميع أعضاء طاقم الإدارة بنجاح.")

async def setup(bot: commands.Bot):
    await bot.add_cog(PointsCog(bot))
