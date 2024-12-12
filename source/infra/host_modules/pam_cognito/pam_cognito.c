//This file is included simply as a wrapper for the extern-ed C functions that
//are a part of the c interface for PAM. it is required first for the functions
//that aren't relevant to authentication but also for eliding the need for
//`const` as that directive doesn't exist in CGO
#include "_cgo_export.h"
#include <stdio.h>

#include <security/pam_modules.h>

GoSlice vargsToSlice(int argc, const char** argv);

PAM_EXTERN int pam_sm_setcred(pam_handle_t *pamh, int flags, int argc, const char **argv ) {
    //printf("pam_sm_setcred\n");
    fflush(0);
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_acct_mgmt(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    //printf("pam_sm_acct_mgmt\n");
    fflush(0);
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_authenticate(pam_handle_t* pamh, int flags, int argc, const char** argv) {
    return smAuthenticate(pamh, flags, argc, (char **)argv);
}

PAM_EXTERN int pam_sm_chauthtok(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    //printf("pam_sm_chauthtok\n");
    //fflush(0);
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_open_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    //printf("pam_sm_open_session\n");
    //fflush(0);
    return PAM_SUCCESS;
}

PAM_EXTERN int pam_sm_close_session(pam_handle_t *pamh, int flags, int argc, const char **argv) {
    //printf("pam_sm_close_session\n");
    //fflush(0);
    return PAM_SUCCESS;
}
