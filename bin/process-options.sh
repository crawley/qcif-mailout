# Helper script for the mailout wrappers.
ARGS=
MARGS=
ANNOUNCE=
MESSAGE=

while [ $# -gt 0 ] ; do
    case $1 in
        --debug|-d|--no-dry-run|-y|--print-only|---summarize-only)
            MARGS="$MARGS $1"
            shift
            ;;
        -C|--cc|-T|--test-to|-l|--limit|--skip-to|--property|-p|--sender)
            MARGS="$MARGS $1 $2"
            shift 2
            ;;
        --message)
            MESSAGE=$2
            shift 2
            ;;
        --article)
            ARTICLE=$2
            shift 2
            ;;
        *)
            break
            ;;
    esac
done
