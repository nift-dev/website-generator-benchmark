#define _GNU_SOURCE
#include <sys/wait.h>
#include <sys/resource.h>
#include <time.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>
static long long ns(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return (long long)t.tv_sec*1000000000LL+t.tv_nsec; }
int main(int argc,char **argv) {
 if(argc<3) return 125;
 FILE *report=fopen(argv[1],"w"); if(!report) return 125;
 long long start=ns(); pid_t pid=fork();
 if(pid<0) return 125;
 if(pid==0) { fclose(report); execvp(argv[2],argv+2); _exit(errno==ENOENT?127:126); }
 int status; struct rusage u; pid_t got;
 do { got=wait4(pid,&status,0,&u); } while(got<0 && errno==EINTR);
 long long end=ns(); if(got<0) return 125;
 int code=WIFEXITED(status)?WEXITSTATUS(status):128+WTERMSIG(status);
 fprintf(report,"{\"wall_ms\":%.9f,\"peak_rss_kib\":%ld,\"cpu_ms\":%.6f,\"exit_code\":%d}\n",(end-start)/1e6,u.ru_maxrss,
  1000.0*(u.ru_utime.tv_sec+u.ru_stime.tv_sec)+(u.ru_utime.tv_usec+u.ru_stime.tv_usec)/1000.0,code);
 fclose(report); return code;
}
