#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>
int main(int argc,char **argv){@autoreleasepool {if(argc!=2)return 2;int pid=atoi(argv[1]);NSArray *all=CFBridgingRelease(CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly,kCGNullWindowID));NSMutableArray *rows=[NSMutableArray array];for(NSDictionary *d in all){if([d[(id)kCGWindowOwnerPID] intValue]==pid){[rows addObject:d];}}NSData *json=[NSJSONSerialization dataWithJSONObject:rows options:0 error:nil];fwrite(json.bytes,1,json.length,stdout);return 0;}}
