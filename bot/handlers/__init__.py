from aiogram import Router

from . import account, admin, market, menu, signup, start, wallet


def get_root_router() -> Router:
    """Collect every feature router in one place.

    Order matters: /start goes first so it works even in the middle of a flow,
    and the menu-button routers (menu, wallet) come before the routers that
    wait for typed answers (account, market) so pressing a menu button during
    the bank-info or buy/sell flow isn't mistaken for an answer.
    To add a feature: create handlers/<feature>.py exposing `router`,
    then include it below.
    """
    root = Router(name="root")
    root.include_router(start.router)
    root.include_router(admin.router)
    root.include_router(signup.router)
    root.include_router(menu.router)
    root.include_router(wallet.router)
    root.include_router(account.router)
    root.include_router(market.router)
    return root
