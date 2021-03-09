from django.shortcuts import render
from openstates.data.models import LegislativeSession, Person
from utils.common import abbr_to_jid, sessions_with_bills, states
from people_admin.models import UnmatchedName


def people_list(request):
    state_people_data = {}

    for state in states:
        state_people_data[state.abbr.lower()] = {
            "state": state.name,
        }

    return render(
        request,
        "people_admin/people_listing.html",
        {"state_people_data": state_people_data},
    )


def people_matcher(request, state):
    jid = abbr_to_jid(state)
    all_sessions = sessions_with_bills(jid)
    if all_sessions:
        session = all_sessions[0]
        unmatched = UnmatchedName.objects.filter(session_id=session)
        state_sponsors = Person.objects.filter(current_jurisdiction_id=jid)

    context = {
        "state": state,
        "session": session,
        "all_sessions": all_sessions,
        "unmatched": unmatched,
        "state_sponsors": state_sponsors,
    }

    return render(request, "people_admin/people_matcher.html", context)


def people_matcher_session(request, state, session):
    jid = abbr_to_jid(state)
    all_sessions = sessions_with_bills(jid)

    session = LegislativeSession.objects.get(identifier=session, jurisdiction_id=jid)

    unmatched = UnmatchedName.objects.filter(session_id=session)

    state_sponsors = Person.objects.filter(current_jurisdiction_id=jid)

    context = {
        "state": state,
        "session": session,
        "all_sessions": all_sessions,
        "unmatched": unmatched,
        "state_sponsors": state_sponsors,
    }

    return render(request, "people_admin/people_matcher.html", context)


# pseudo-code for apply_match view:

# @require_POST
# def apply_match(request):
#     button = request.POST["submit_button"]
#     match_id = request.POST["match_id"]
#     unmatched_id = request.POST["unmatched_id"]

#     unmatched_name = get_object_or_404(UnmatchedName, pk=unmatched_id)

#     if button == "match":
#         unmatched_name.person_id = match_id
#     elif button == "source_error":
#         unmatched_name.status = NameStatus.UNMATCHED
#     else:
#         ...

#     unmatched_name.save()

#     return JSONResponse({"status": "success"})
