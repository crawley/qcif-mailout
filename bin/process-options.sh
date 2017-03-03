# Helper script for the mailout wrappers.
ARGS=
MARGS=

while [ $# -gt 0 ] ; do
    case $1 in
        --debug|-d|--no-dry-run|-y|--print-only|---summarize-only)
            MARGS="$MARGS $1"
            shift
            ;;
        -T|--test-to|-l|--limit|--skip-to|--property|-p)
            MARGS="$MARGS $1 $2"
            shift 2
            ;;
        -*)
            echo unrecognized option $1
            exit 1
            ;;
        *)
            break
            ;;
    esac
done
